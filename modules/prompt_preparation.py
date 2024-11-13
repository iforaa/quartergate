# import fitz  # PyMuPDF
import base64
from mimetypes import guess_type
from io import BytesIO
# from PIL import Image


class PromptPreparation:
    def __init__(self, init_prompt):
        self.content = [{"type": "text", "text": init_prompt}]  # Initialize with the initial prompt

    def process_txt(self, content):
        self.content.append({"type": "text", "text": content})

    def process_file(self, file_path):
        """
        Process a single file and add its content to the prompt array.
        :param file_path: Path to the file to process.
        """
        if file_path.endswith(".pdf"):
            self._process_pdf(file_path)
        elif file_path.endswith(".txt"):
            self._process_txt(file_path)
        else:
            print(f"Unsupported file type: {file_path}")

    def get_prompt_array(self):
        """
        Get the prepared prompt array.
        :return: List of dictionaries representing the prompt array.
        """
        return self.content

    # def _process_pdf(self, pdf_path):
        # """
        # Extract text from a PDF file and add it to the content array.
        # :param pdf_path: Path to the PDF file.
        # """
        # print(f"Processing PDF: {pdf_path}")
        # doc = fitz.open(pdf_path)
        # for page_num in range(len(doc)):
        #     page = doc[page_num]

        #     # Extract text from the page
        #     text_content = page.get_text()

        #     # Append the extracted text to the content array
        #     self.content.append({
        #         "type": "text",
        #         "text": text_content.strip()  # Strip to clean up extra whitespace
        #     })
        # doc.close()

    # def _process_pdf(self, pdf_path):
    #     """
    #     Convert a PDF to in-memory JPEG images, encode them in base64, and add to the prompt array.
    #     :param pdf_path: Path to the PDF file.
    #     """
    #     print(f"Processing PDF: {pdf_path}")
    #     doc = fitz.open(pdf_path)
    #     for page_num in range(len(doc)):
    #         page = doc[page_num]
    #         pix = page.get_pixmap()

    #         # Convert pixmap to in-memory JPEG
    #         image_data = self._pixmap_to_jpeg(pix)

    #         # Encode image and append to content
    #         mime_type, img_b64_str = self._encode_image_base64(image_data)
    #         self.content.append({
    #             "type": "image_url",
    #             "image_url": {"url": f"data:{mime_type};base64,{img_b64_str}"}
    #         })
    #     doc.close()

    # def _pixmap_to_jpeg(self, pix):
    #     """
    #     Convert a PyMuPDF pixmap to in-memory JPEG image.
    #     :param pix: PyMuPDF Pixmap object.
    #     :return: BytesIO object containing the JPEG image data.
    #     """
    #     img = Image.frombytes("RGB", [pix.width, pix.height], pix.samples)
    #     image_data = BytesIO()
    #     img.save(image_data, format="JPEG")
    #     image_data.seek(0)
    #     return image_data

    def _process_txt(self, txt_path):
        """
        Read a TXT file and add its content to the prompt array.
        :param txt_path: Path to the TXT file.
        """
        print(f"Processing TXT: {txt_path}")
        with open(txt_path, "r", encoding="utf-8") as f:
            text_content = f.read()
        self.content.append({"type": "text", "text": text_content})

    def _encode_image_base64(self, image_data):
        """
        Encode in-memory image data to base64.
        :param image_data: BytesIO object containing the image data.
        :return: Tuple of MIME type and base64 string.
        """
        mime_type = "image/jpeg"
        img_b64_str = base64.b64encode(image_data.getvalue()).decode("utf-8")
        return mime_type, img_b64_str
