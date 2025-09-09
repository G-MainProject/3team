
import json
import csv
import sys

json_path = r'c:\Users\3CLASS_008\Documents\GitHub\3team\Python\Prediction\SentiWord_info.json'
csv_path = r'c:\Users\3CLASS_008\Documents\GitHub\3team\Python\Analyze\SentiWord_summary.csv'

try:
    with open(json_path, 'r', encoding='utf-8') as f_in:
        data = json.load(f_in)
    
    with open(csv_path, 'w', newline='', encoding='utf-8') as f_out:
        writer = csv.writer(f_out)
        writer.writerow(['word', 'polarity'])
        for item in data:
            writer.writerow([item.get('word', ''), item.get('polarity', '')])
            
    print(f"Successfully created {csv_path}")

except Exception as e:
    print(f"An error occurred: {e}", file=sys.stderr)
