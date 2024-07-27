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
PRINTER_IP_LARGE = os.getenv('PRINTER_IP_LARGE')
PRINTER_IP_SMALL = os.getenv('PRINTER_IP_SMALL')
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

def create_zpl_label_large(item_name, item_code, supplier_name, supplier_part_no):
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

def create_zpl_label_small(item_name, item_code, supplier_name, supplier_part_no):
    return f"""
        ^XA
        ^FO20,10
        ^BQN,2,4
        ^FDQA,{item_code}^FS

        ^FO130,20^A0N,60,65
        ^FB696,2,0,L,0
        ^FD{item_name}^FS

        ^FO20,145^A0N,24,24^FDERP-Teilenummer:^FS
        ^FO20,175^A0N,30,30^FD{item_code}^FS

        ^FO350,145^A0N,24,24^FD{supplier_name}^FS
        ^FO350,175^A0N,30,30^FD{supplier_part_no}^FS
        ^XZ
        """
def create_zpl_label_small_screw(item_code, screw_norm, screw_thread, screw_length, screw_material, screw_strength, screw_surface):
    return f"""
       ^XA
        ^FO146,10^GB{screw_length},5,5^FS
        
        ^CF0,130
        ^FO140,24^FB667,2,0,L^FD{screw_thread} x {screw_length}^FS
        ^BQN,2,4^FO15,0^FDQA,{item_code}^FS
        ^FO0,140^GB850,3,3^FS
        
        ^CF0,55
        ^FO20,160^FD{screw_norm}^FS
        
        ^CF0,55
        ^FO650,20^FD{screw_material}^FS
        ^FO650,80^FD{screw_surface}^FS
        ^FO650,160^FD{screw_strength}^FS
        
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
    label_type = request.form.get('label_type', 'large')

    results = []
    for item_code in item_codes:
        try:
            item_data = fetch_item_data(item_code)
            item_name = item_data.get('item_name')
            
            
            if label_type == 'large':
                supplier_data = item_data.get('supplier_items')[0]
                supplier_name = supplier_data.get('supplier')
                supplier_part_no = supplier_data.get('supplier_part_no')
                zpl_label = create_zpl_label_large(item_name, item_code,supplier_name, supplier_part_no)
                printer_ip = PRINTER_IP_LARGE
            elif label_type == 'small':
                supplier_data = item_data.get('supplier_items')[0]
                supplier_name = supplier_data.get('supplier')
                supplier_part_no = supplier_data.get('supplier_part_no')
                zpl_label = create_zpl_label_small(item_name, item_code,supplier_name, supplier_part_no)
                printer_ip = PRINTER_IP_SMALL
            elif label_type == 'screw':
                attributes = item_data.get('attributes', [])
                screw_norm = attributes[0]['attribute_value']
                screw_thread = attributes[1]['attribute_value']
                screw_length = attributes[2]['attribute_value']
                screw_material = attributes[3]['attribute_value']
                screw_strength = attributes[4]['attribute_value']
                screw_surface = attributes[5]['attribute_value']
                zpl_label = create_zpl_label_small_screw(item_code, screw_norm, screw_thread, screw_length, screw_material, screw_strength, screw_surface)
                printer_ip = PRINTER_IP_SMALL

            send_to_printer(zpl_label, printer_ip, PRINTER_PORT)
            results.append(f"Label for {item_code} sent to printer successfully.")
        except Exception as e:
            results.append(f"Error processing {item_code}: {e}")

    return jsonify(results)

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=5000)
