from flask import Flask, request, render_template, jsonify
import os
import requests
from requests.auth import HTTPBasicAuth
import socket
from dotenv import load_dotenv

app = Flask(__name__)

# Load environment variables from .env file
load_dotenv()

# ERPNext API configuration
ERP_URL = os.getenv('ERP_URL')
API_KEY = os.getenv('API_KEY')
API_SECRET = os.getenv('API_SECRET')

# Printer configuration
PRINTER_IP = os.getenv('PRINTER_IP')
PRINTER_PORT = int(os.getenv('PRINTER_PORT', 9100))

def fetch_item_data(item_code):
    url = f"{ERP_URL}/api/resource/Item/{item_code}"
    response = requests.get(url, auth=HTTPBasicAuth(API_KEY, API_SECRET))
    
    if response.status_code == 200:
        try:
            item_data = response.json().get('data')
            return item_data
        except ValueError:
            raise Exception("Invalid JSON response")
    else:
        raise Exception(f"Failed to fetch data: {response.status_code} {response.text}")

def create_zpl_label(item_name, item_code, supplier_name, supplier_part_no):
    return f"""
^XA
^PW1060

^LL365
^FO950,245
^BQN,2,5
^FDQA,{item_code}^FS

^FO10,20^A0N,95,100
^FB1104,2,0,L,0
^FD{item_name}^FS

^FO10,260^A0N,36,36^FDERP-Teilenummer:^FS
^FO10,310^A0N,50,50^FD{item_code}^FS

^FO400,260^A0N,36,36^FD{supplier_name}^FS
^FO400,310^A0N,50,50^FD{supplier_part_no}^FS
^XZ
"""

def send_to_printer(zpl_label, printer_ip, printer_port=9100):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.connect((printer_ip, printer_port))
        s.sendall(zpl_label.encode('utf-8'))

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/print_labels', methods=['POST'])
def print_labels():
    item_codes_input = request.form.get('item_codes', '')
    item_codes = item_codes_input.replace('\n', ',').split(',')
    item_codes = [code.strip() for code in item_codes]  # Remove any surrounding whitespace

    results = []
    for item_code in item_codes:
        try:
            item_data = fetch_item_data(item_code)
            item_name = item_data.get('item_name')
            supplier_data = item_data.get('supplier_items')[0]
            supplier_name = supplier_data.get('supplier')
            supplier_part_no = supplier_data.get('supplier_part_no')

            zpl_label = create_zpl_label(item_name, item_code, supplier_name, supplier_part_no)
            send_to_printer(zpl_label, PRINTER_IP, PRINTER_PORT)
            results.append(f"Label for {item_code} sent to printer successfully.")
        except Exception as e:
            results.append(f"Error processing {item_code}: {e}")

    return jsonify(results)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
