from modules.directory_monitor import DirectoryMonitor
import os
from modules.prompt_preparation import PromptPreparation
from modules.chatgpt import *
from modules.tgbot import *
import asyncio
import requests
import psycopg2
from finance_calendars import finance_calendars as fc
from datetime import datetime, timedelta
import time
from dotenv import load_dotenv
load_dotenv()


api_key = os.getenv('API_NINJAS_TOKEN')

cloudflare_worker_url = os.getenv('DATA_STORE_URL')
ninjas_url = os.getenv('API_NINJAS_URL')

db_params = {
    "dbname": os.getenv('NEON_DB_NAME'),
    "user": os.getenv('NEON_USER'),
    "password": os.getenv('NEON_PASSWORD'),
    "host": os.getenv('NEON_HOST'),
    "port":os.getenv('NEON_PORT'),
    "sslmode": "require",
}

# Check and fetch transcript
def fetch_or_save_transcript(ticker, year, quarter):
    try:
        filename = f"{ticker}_{year}_Q{quarter}_earnings_call.txt"

        # Connect to the database
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()

        # Check if the transcript already exists in the database
        select_query = """
        SELECT id, filename FROM transcripts
        WHERE ticker = %s AND year = %s AND quarter = %s;
        """
        cursor.execute(select_query, (ticker, year, quarter))
        result = cursor.fetchone()

        if result:
            print("Transcript fetched from the database.")
            transcript_id, existing_filename = result
            worker_response = requests.get(f'{cloudflare_worker_url}/download/{filename}').text
            # print(f'WORK_RESP: {worker_response}')
            return transcript_id, worker_response  # Return the transcript content

        # If not found, fetch from the API
        api_url = f'{ninjas_url}/earningstranscript?ticker={ticker}&year={year}&quarter={quarter}'
        response = requests.get(api_url, headers={'X-Api-Key': api_key})

        if response.status_code == requests.codes.ok and response.json():
            transcript = response.json().get("transcript", None)

            if transcript:

                worker_response = requests.post(
                    f'{cloudflare_worker_url}/upload',
                    files={"file": (filename, transcript)},
                )

                # Insert the transcript into the database
                insert_query = """
                INSERT INTO transcripts (ticker, year, quarter, created_at, filename)
                VALUES (%s, %s, %s, NOW(), %s) RETURNING id;
                """
                cursor.execute(insert_query, (ticker, year, quarter, filename))
                transcript_id = cursor.fetchone()[0]
                connection.commit()
                print("Transcript saved to the database.")
                return transcript_id, transcript  # Return the transcript content

            else:
                print("No transcript available for this request.")
                return None, None
        else:
            print("API error:", response.status_code, response.text)
            return None, None

    except Exception as db_error:
        print("Database error:", db_error)
        return None, None

    finally:
        if connection:
            connection.close()
            print("Database connection closed.")

def get_earnings_symbols(date=None, days_ago=None):
    if days_ago is not None:
        target_date = datetime.now() - timedelta(days=days_ago)
    elif date is not None:
        target_date = date
    else:
        target_date = datetime.now()

    target_date = target_date.replace(hour=0, minute=0, second=0, microsecond=0)
    earnings = fc.get_earnings_by_date(target_date)
    data = []
    for symbol in earnings.index:
        row = earnings.loc[symbol]
        fiscal_quarter = row['fiscalQuarterEnding']
        try:
            fiscal_year, fiscal_quarter_number = parse_fiscal_data(fiscal_quarter)
            data.append({
                'ticker': symbol,
                'fiscal_year': fiscal_year,
                'fiscal_quarter': fiscal_quarter_number
            })
        except Exception as db_error:
            print("Error parsing fiscal data:", db_error)
            continue
    return data

def parse_fiscal_data(fiscal_quarter):
    """
    Parse fiscal year and quarter from the `fiscalQuarterEnding` field.

    Args:
        fiscal_quarter (str): A string like 'Sep/2024'.

    Returns:
        tuple: Fiscal year (int) and fiscal quarter (int).
    """
    month, year = fiscal_quarter.split('/')
    year = int(year)

    # Map all months to their respective quarters
    month_to_quarter = {
        'Jan': 1, 'Feb': 1, 'Mar': 1,
        'Apr': 2, 'May': 2, 'Jun': 2,
        'Jul': 3, 'Aug': 3, 'Sep': 3,
        'Oct': 4, 'Nov': 4, 'Dec': 4,
    }

    # Get the first three characters of the month and map to a quarter
    quarter = month_to_quarter[month[:3]]

    return year, quarter

async def process_todays_transcripts(days_ago=1, max_symbols=3):

    symbols_today = get_earnings_symbols(days_ago=days_ago)

    print(f"Processing {min(max_symbols, len(symbols_today))} symbols from {days_ago} day(s) ago.")
    connection = psycopg2.connect(**db_params)
    cursor = connection.cursor()

    for index, symbol in enumerate(symbols_today[:max_symbols], start=1):
        ticker = symbol['ticker']
        year = symbol['fiscal_year']
        quarter = symbol['fiscal_quarter']

        filename = f"{ticker}_{year}_Q{quarter}_summary.txt"

        # Connect to the database


        select_query = """
        SELECT filename FROM summaries
        WHERE ticker = %s AND year = %s AND quarter = %s;
        """
        cursor.execute(select_query, (ticker, year, quarter))
        result = cursor.fetchone()

        if result:
            print("Article fetched from the database.")
            worker_response = requests.get(f'{cloudflare_worker_url}/download/{filename}').text
            # print(f'WORK_RESP: {worker_response}')
            message = f"📢 New Update for Ticker: {ticker}\n\n{worker_response}"
            await publish_to_telegram(message)
        else:
            # Fetch or save the transcript


            prompt_preparation = PromptPreparation(
                f"""
                Imagine you are a financial analyst tasked with analyzing the following data for the ticker {ticker}. Your goal is to identify key financial results, successes, challenges, and future plans.

                Start with a clear and engaging title.
                Summarize the main financial results at the top, prioritizing clarity and relevance.
                Highlight key successes and notable failures from the provided information, along with any insights into future plans or strategies.
                If the data includes an earnings call, summarize the Q&A session by focusing on the most critical questions and answers.
                Convert non-USD currencies to USD for consistency.
                Provide additional context for the audience:

                Brief overviews of countries (GDP, population, region) or companies (primary revenue sources, locations) mentioned.
                Simplified explanations of complex financial terms as if explaining to a beginner.
                Make the article engaging, clear, and easy to understand. You can use emojis to emphasize points but avoid using Markdown formatting.
                """
            )

            transcript_id, transcript = fetch_or_save_transcript(ticker, year, quarter)
            if transcript == None:
                continue
            print(f'ID: {transcript_id} TRANSCRIPT: {len(transcript)}')

            prompt_preparation.process_txt(transcript)
            content = prompt_preparation.get_prompt_array()
            gpt_response = send_message(content)
            insert_query = """
            INSERT INTO summaries (ticker, year, quarter, filename)
            VALUES (%s, %s, %s, %s) RETURNING id;
            """
            cursor.execute(insert_query, (ticker, year, quarter, filename))
            summary_id = cursor.fetchone()[0]
            print(f'SUMMARY_ID: {summary_id}')



            connection.commit()

            insert_source_query = """
                INSERT INTO summary_sources (summary_id, source_type, source_id)
                VALUES (%s, %s, %s);
            """
            cursor.execute(insert_source_query, (summary_id, "transcript", transcript_id))
            connection.commit()

            requests.post(
                f'{cloudflare_worker_url}/upload',
                files={"file": (filename, gpt_response)},
            )
            message = f"📢 New Update for Ticker: {ticker}\n\n{gpt_response}"
            await publish_to_telegram(message)

        await asyncio.sleep(5)

    if connection:
        connection.close()


if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(process_todays_transcripts(days_ago=1, max_symbols=5))
