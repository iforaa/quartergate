import os
from telegram import Bot
import re
from telegram.constants import ParseMode
from dotenv import load_dotenv


bot_token = os.getenv('TG_BOT_TOKEN')
channel_id = os.getenv('TG_CHANNEL_ID')  # Replace with your channel username or ID
bot = Bot(token=bot_token)

def convert_to_telegram_markdown(text):
    """
    Converts standard Markdown to Telegram MarkdownV2, ensuring only unsupported special characters are escaped,
    while retaining valid MarkdownV2 syntax.
    """
    # Step 2: Remove unsupported Markdown syntax
    text = text.replace('####', '')  # Remove headings like ###
    text = text.replace('###', '')
    text = text.replace('##', '')
    text = text.replace('#', '')

    # Step 1: Replace standard Markdown syntax with Telegram MarkdownV2 equivalents
    replacements = [
        (r'\*\*(.+?)\*\*', r'*\1*'),  # Bold (**text** -> *text*)
        (r'_(.+?)_', r'_\1_'),        # Italic (_text_ -> _text_)
        (r'~~(.+?)~~', r'~\1~'),      # Strikethrough (~~text~~ -> ~text~)
        (r'`(.+?)`', r'`\1`'),        # Inline code (`text` -> `text`)
        (r'```([\s\S]+?)```', r'```\1```'),  # Code block
        (r'\[(.+?)\]\((.+?)\)', r'[\1](\2)'),  # Inline links ([text](url) -> [text](url))
    ]

    for pattern, replacement in replacements:
        text = re.sub(pattern, replacement, text, flags=re.DOTALL)




    # Step 3: Escape Telegram MarkdownV2 special characters not part of the markup
    # Characters to escape: `_`, `*`, `[`, `]`, `(`, `)`, `~`, `>`, `#`, `+`, `-`, `=`, `|`, `{`, `}`, `.`, `!`
    # Except when they are part of valid Telegram MarkdownV2 syntax
    special_characters = r'_*\[\]()~>#+-=|{}.!'
    escaped_text = re.sub(f'([{re.escape(special_characters)}])', r'\\\1', text)

    # Step 4: Restore valid MarkdownV2 syntax that was escaped
    valid_syntax = [
        (r'\\\*', r'*'),  # Bold/Italic asterisks
        (r'\\_', r'_'),   # Italic underscores
        (r'\\~', r'~'),   # Strikethrough
        (r'\\`', r'`'),   # Inline code
        (r'\\\[', r'['),  # Inline links
        (r'\\\]', r']'),  # Inline links
#        (r'\\\(', r'('),  # Inline links
#        (r'\\\)', r')'),   Inline links
    ]

    for pattern, replacement in valid_syntax:
        escaped_text = re.sub(pattern, replacement, escaped_text)

    return escaped_text




def split_message_by_paragraphs(message, max_chunk_size=4096):
    """
    Splits a long message into smaller chunks by paragraphs, ensuring each chunk
    does not exceed the max_chunk_size.
    """
    paragraphs = message.split('\n')  # Split message by newlines into paragraphs
    chunks = []
    current_chunk = ""

    for paragraph in paragraphs:
        if len(current_chunk) + len(paragraph) + 1 > max_chunk_size:
            # If adding this paragraph exceeds the limit, finalize the current chunk
            chunks.append(current_chunk.strip())
            current_chunk = paragraph  # Start a new chunk
        else:
            # Add paragraph to the current chunk
            current_chunk += f"\n{paragraph}"

    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk.strip())

    return chunks

async def publish_to_telegram(message, file_path=None):
    """
    Publish a message (and optional file) to a Telegram channel.
    """
    try:
        escaped_message = convert_to_telegram_markdown(message)

        print(message)
        print(escaped_message)
        if file_path and os.path.exists(file_path):
            # Send the file with a caption
            await bot.send_document(chat_id=channel_id, document=open(file_path, "rb"), caption=escaped_message[:1024])
            # Caption must be within 1024 characters
        else:
            # Split the message by paragraphs and send in chunks
            chunks = split_message_by_paragraphs(escaped_message)
            for chunk in chunks:
                await bot.send_message(chat_id=channel_id, text=chunk, parse_mode=ParseMode.MARKDOWN_V2)
        print("Message sent successfully.")
    except Exception as e:
        print(f"Failed to send message: {e}")
