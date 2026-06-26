import base64
import mimetypes
import os
from mistralai.client import Mistral

def extract_text_from_image(image_path, prompt="Extract ALL text visible in this image. Return only the extracted text, nothing else.", model="pixtral-12b-2409"):
    """
    Extract text from an image using Mistral's vision API (pixtral-12b-2409).
    
    Args:
        image_path (str): Path to the local image file (e.g., 'amul_paneer.png')
        prompt (str): Custom instruction for text extraction. 
                     Defaults to extracting all visible text.
    
    Returns:
        str: Extracted text from the image
        
    Raises:
        FileNotFoundError: If the image file doesn't exist
        Exception: If the API call fails
        
    Example:
        >>> text = extract_text_from_image("product_label.png")
        >>> print(text)
    """
    
    # Validate file exists
    if not os.path.isfile(image_path):
        raise FileNotFoundError(f"Image file not found: {image_path}")
    
    # Initialize Mistral client
    mistral_client = Mistral(api_key=os.getenv("MISTRAL_API_KEY"))
    
    # Read and encode image to base64
    with open(image_path, "rb") as image_file:
        image_data = base64.standard_b64encode(image_file.read()).decode("utf-8")
    mime_type = mimetypes.guess_type(image_path)[0] or "image/png"
    
    # Call Mistral vision API
    message = mistral_client.chat.complete(
        model=model,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "text",
                        "text": prompt
                    },
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:{mime_type};base64,{image_data}"
                        }
                    }
                ]
            }
        ]
    )
    
    # Extract and return the response
    return message.choices[0].message.content
