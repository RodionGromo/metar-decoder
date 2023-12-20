import datetime, requests

weather_trends = {
	"NOSIG": "No significant change",
	"TEMPO": "Temporary weather",
	"BECMG": "Something is coming"
}

weather_cnds = {
	"BL": "blowing",
	"SH": "showering",
	"FZ": "freezing",
	"VC": "in vicinity",
	"MI": "shallow",
	"PR": "aerodrome partially covered by",
	"BC": "patches",
	"DR": "low drifting",
	"DZ": "drizzle",
	"RA": "rain",
	"SN": "snow",
	"SG": "snow grains",
	"PL": "ice pellets",
	"GS": "small hail",
	"GR": "Hail",
	"DS": "duststorm",
	"SS": "sandstorm",
	"FG": "fog",
	"BR": "mist",
	"HZ": "haze",
	"FU": "smoke",
	"DU": "dust",
	"SQ": "squall",
	"IC": "ice crystals",
	"TS": "thunderstorm",
	"VA": "Volcanic ash",
}

cloud_cnds = {
	"CLR": "clear",
	"FEW": "few",
	"SCT": "scattered",
	"BKN": "broken",
	"OVC": "overcast"
}

cloud_cnds2 = {
	"CB": "cumulonimbus cloud",
	"TCU": "towering cumulus",
	"ACC": "altocumulus castellanus"
}

rw_deps = [
	"clean and dry",
	"damp",
	"wet or water patches",
	"rime or frost covered",
	"dry snow",
	"wet snow",
	"slush",
	"ice",
	"compacted snow",
	"ruts"
]

rw_cntr = {
	1: [0, 10],
	2: [11, 25],
	5: [26, 50],
	9: [51, 100]
}


def parse(json_data):
	raw_date, raw_data, _ = json_data["metar"].split("\n")
	report_date = datetime.datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")

	raw_data = raw_data.split(" ")
	parse_index = 0
	data = dict()
	data["callcode"] = raw_data[parse_index]
	parse_index += 1
	data["datetime"] = datetime.datetime.strptime(raw_data[parse_index][:-1], "%d%H%M")
	parse_index += 1

	# wind params
	wind_data = raw_data[parse_index]
	data["wind_heading"] = int(wind_data[:3])
	data["wind_speed"] = int(wind_data[3:5])
	if wind_data[5] == "G":
		data["wind_gusts"] = int(wind_data[6:8])
		data["wind_units"] = wind_data[8:]
	else:
		data['wind_units'] = wind_data[5:]
	parse_index += 1
	next_data = raw_data[parse_index]
	if "V" in next_data:
		data["wind_variancy"] = [int(next_data[:3]), int(next_data[4:])]
		parse_index += 1

	# visibility
	visibility_data = raw_data[parse_index]
	data["visibility"] = int(visibility_data)
	parse_index += 1

	# weather
	raw_weather_status = raw_data[parse_index]
	data["weather_severity"] = "medium"
	statuses = []
	if raw_weather_status[0] in ["-", "+"]:
		if raw_weather_status[0] == "-":
			data["weather_severity"] = "light"
		else:
			data["weather_severity"] = "heavy"
	for stat in [raw_weather_status[i:i + 2] for i in range(1, len(raw_weather_status), 2)]:
		if stat in weather_cnds.keys():
			statuses.append(weather_cnds[stat])
	data["weather_conditions"] = statuses
	if not statuses:
		del data["weather_severity"]
		del data["weather_conditions"]
	parse_index += int("weather_severity" in data.keys())

	# cloudiness (can be more than one)
	data["cloudiness"] = []
	while True:
		raw_cloudiness = raw_data[parse_index]
		cloudiness_status = []
		cl_stat = raw_cloudiness[:3]
		if cl_stat in cloud_cnds.keys():
			cloudiness_status.append(cloud_cnds[cl_stat])
		else:
			break
		cloudiness_status.append(int(raw_cloudiness[3:6]) * 100)
		additional_data = raw_cloudiness[6:]
		if additional_data in cloud_cnds2.keys():
			cloudiness_status.append(cloud_cnds2[additional_data])
		elif additional_data != "":
			cloudiness_status.append(f" undefined cnd: {additional_data}")
		data["cloudiness"].append(cloudiness_status)
		parse_index += 1

	# temperature
	print(raw_data[parse_index])
	air_temp, dew_temp = raw_data[parse_index].split("/")
	if ("M" in air_temp):
		data["air_temp"] = -int(air_temp[1:])
	else:
		data["air_temp"] = int(air_temp)

	if ("M" in dew_temp):
		data["dew_temp"] = -int(dew_temp[1:])
	else:
		data["dew_temp"] = int(dew_temp)
	parse_index += 1

	# pressure
	pressure_data = raw_data[parse_index]
	data["pressure"] = [int(pressure_data[1:])]
	if pressure_data[0] == "Q":
		data["pressure"].append("hPa")
	elif pressure_data[0] == "A":
		data["pressure"].append("inHg")
	parse_index += 1

	# runway stats
	data["runway_stats"] = []
	while True:
		runway_state = dict()
		runway_data = raw_data[parse_index]
		if runway_data[0] != "R":
			break
		runway_state["id"] = runway_data[1:runway_data.index("/")]
		runway_data = runway_data[runway_data.index("/") + 1:]
		runway_state["deposits"] = rw_deps[int(runway_data[0])]
		runway_state["contamination_range"] = rw_cntr[int(runway_data[1])]
		cnt_depth = int(runway_data[2:4])
		if 0 < cnt_depth <= 90:
			runway_state["contamination_depth"] = [cnt_depth, "mm"]
		elif 91 < cnt_depth < 99:
			runway_state["contamination_depth"] = [(cnt_depth - 90) * 5, "cm"]
		elif cnt_depth == 99:
			runway_state["contamination_depth"] = [-1, "not usable"]
		elif cnt_depth == 0:
			runway_state["contamination_depth"] = [0, "not significant"]
		friction_coeff = int(runway_data[4:6])
		if 0 < friction_coeff < 90:
			runway_state["friction_coefficient"] = friction_coeff / 100
		elif 90 < friction_coeff <= 95:
			runway_state["friction_coefficient"] = friction_coeff - 90 * 0.05

		data["runway_stats"].append(runway_state)
		parse_index += 1

	# weather trend
	wtread = raw_data[parse_index]
	data["weather_trend"] = weather_trends[wtread]

	return report_date, data

def writereportfor(ask: str):
	json_data = requests.get(f"https://metartaf.ru/{ask.upper()}.json").json()
	print(json_data["metar"])
	date, data = parse(json_data)

	print("report:")
	for key, value in data.items():
		if type(value) == list:
			print(f"{key}:")
			for obj in value:
				if type(obj) == dict:
					for key2, value2 in obj.items():
						print(f"\t{key2}: {value2}")
				else:
					print("\t", obj, end="")
				print()
		else:
			print(f"{key}: {value}")
'''
Москва:
	uudd - домодедово
	uuee - шереметьево
Санкт-Питербург:
	ulli - пулково

Белгород:
	uuob - белгород
'''

writereportfor("urss")