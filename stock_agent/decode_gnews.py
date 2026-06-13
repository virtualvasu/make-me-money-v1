import base64
import re
url = "https://news.google.com/rss/articles/CBMiW0FVX3lxTFB5clowaWRtTEd2c2xUTTRBZk10clF6ODFhWDlwV24zd3VpeC1kajRLRnhnYkVsRlBTQXZtQTRoNnZtZXViT2lVUkZKZ0xvUmFrS0NDNENPNFJMalk?oc=5"
encoded_id = url.split("articles/")[1].split("?")[0]
try:
    padding = "=" * ((4 - len(encoded_id) % 4) % 4)
    decoded = base64.urlsafe_b64decode(encoded_id + padding)
    print("Decoded:", decoded)
except Exception as e:
    print(e)
