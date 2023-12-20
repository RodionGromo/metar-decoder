from metar_parser import MetarParser
import requests

def pretty_print_dict(data: dict, height=0):
	height_str = '\t'*height
	for key, value in data.items():
		if type(value) == dict:
			print(f"{height_str}{key}:")
			pretty_print_dict(value, height+1)
		elif type(value) == list:
			print(f"{height_str}{key}:")
			pretty_print_list(value, height+1)
		else:
			print(f"{height_str}{key}: {value}")

def pretty_print_list(data, height=0):
	height_str = '\t'*height
	for obj in data:
		if type(obj) == list:
			pretty_print_list(obj, height+1)
		elif type(obj) == dict:
			print(height_str + str(data.index(obj)),":", sep="")
			pretty_print_dict(obj, height+1)
		else:
			print(f"{height_str}> {obj}")

ask = "EGLL"

json_data = requests.get(f"https://metartaf.ru/{ask.upper()}.json").json()
print(json_data["metar"].split("\n")[1])
parser = MetarParser()
data = parser.parse_metar(json_data)
pretty_print_dict(data)
