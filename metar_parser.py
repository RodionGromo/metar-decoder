import re, datetime

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
	"VA": "Volcanic ash"
}
regex_weather = r"\b(-|\+|)(" + "|".join(weather_cnds.keys()) + r")+\b"

cloud_cnds = {
	"CLR": "clear",
	"FEW": "few",
	"SCT": "scattered",
	"BKN": "broken",
	"OVC": "overcast",
	"NSC": "not important"
}

runway_deps = {
	"0": "clean and dry",
	"1": "damp",
	"2": "wet or water patches",
	"3": "rime or frost covered",
	"4": "dry snow",
	"5": "wet snow",
	"6": "slush",
	"7": "ice",
	"8": "compacted snow",
	"9": "ruts",
	"/": None
}

runway_depcov = {
	"1": (0, 10),
	"2": (11, 25),
	"5": (26, 50),
	"9": (51, 100),
	"/": None
}

runway_waystat = {
	"CLRD": "Cleared", 
	"CLSD": "Closed",
	"SNOKLO": "Closed, snow"
}

weather_trends = {
	"NOSIG": "No significant change",
	"TEMPO": "Temporary weather",
	"BECMG": "Something is coming"
}

class MetarParser():
	def __init__(self):
		self.test = ""

	@staticmethod
	def parse_time(datablock):
		return datetime.datetime.strptime(datablock[:-1], "%d%H%M")

	@staticmethod
	def parse_wind(datablock, severity):
		wind_data = {}
		if severity == 0:
			wind_data["from"] = int(datablock[:3])
			wind_data["speed"] = int(datablock[3:5])
			wind_data["units"] = datablock[5:]
		elif severity == 1:
			wind_data["from"] = int(datablock[:3])
			wind_data["speed"] = int(datablock[3:5])
			wind_data["gust_speed"] = int(datablock[6:8])
			wind_data["units"] = datablock[8:]
		elif severity == 2:
			wind_data["angle_start"] = int(datablock[:3])
			wind_data["angle_end"] = int(datablock[4:])
		elif severity == 3:
			wind_data["angle"] = "varies"
			wind_data["speed"] = int(datablock[3:5])
			wind_data["units"] = datablock[5:]
		return wind_data

	@staticmethod
	def parse_vd(datablock):
		return int(datablock)

	@staticmethod
	def parse_visibility_at(datablock):
		distance = int(datablock[:4])
		heading = datablock[4:]
		return {
			"distance": distance,
			"to": heading
		}

	@staticmethod
	def parse_clouds(datablock):
		if "CAVOK" in datablock:
			return ("good weather", 0)
		if "NSC" in datablock:
			return ("nothing important", 0)
		cloud_state = datablock[:3]
		cloud_height = int(datablock[3:]) * 100
		if cloud_state in cloud_cnds.keys():
			return (cloud_cnds[cloud_state], cloud_height)
		else:
			return (f"undefined: {cloud_state}", cloud_height)

	@staticmethod
	def parse_temperatures(datablock):
		raw_air, raw_dew = datablock.split("/")
		tempData = {}

		if raw_air[0] == "M":
			tempData["air"] = -int(raw_air[1:])
		else:
			tempData["air"] = int(raw_air)

		if raw_dew[0] == "M":
			tempData["dew"] = -int(raw_dew[1:])
		else:
			tempData["dew"] = int(raw_dew)
		return tempData

	@staticmethod
	def parse_pressure(datablock):
		units = datablock[0]
		value = datablock[1:]
		return (
			"hPa" if units == "Q" else "inHg",
			int(value)
		)

	@staticmethod
	def parse_runway(datablock):
		runway_callcode, runway_stat = datablock.split("/", 1)
		runway_data = {}
		runway_data["id"] = runway_callcode
		if(runway_stat[:4] not in runway_waystat.keys()):
			runway_data["deposits"] = runway_deps[runway_stat[0]]
			runway_data["deposit_coverage"] = runway_depcov[runway_stat[1]]
			try:
				dep_th = int(runway_stat[2:4])
				if 0 <= dep_th <= 90:
					runway_data["deposit_thickness"] = (dep_th, "mm")
				elif 92 <= dep_th <= 96:
					runway_data["deposit_thickness"] = ((dep_th-90)*5, "cm")
			except ValueError:
				runway_data["deposit_thickness"] = None
		else:
			runway_data["runway_status"] = runway_waystat[runway_stat[:4]]

		try:
			runway_gripcoeff = int(runway_stat[4:6])
			if 0 < runway_gripcoeff <= 90:
				runway_data["grip_coeff"] = runway_gripcoeff / 100
			if 90 < runway_gripcoeff <= 95:
				runway_data["grip_coeff"] = (runway_gripcoeff - 90) * .04
		except ValueError:
			runway_data["grip_coeff"] = 0


		return runway_data

	@staticmethod
	def parse_trend(datablock):
		return weather_trends[datablock]

	@staticmethod
	def parse_weather(datablock):
		severity = "heavy" if datablock[0] == "+" else "light" if datablock[0] == "-" else "medium"
		startIndex = 0 if severity == "medium" else 1
		datablock = datablock[startIndex:]
		conditions = []
		for cnd in [datablock[i:i+2] for i in range(0, len(datablock), 2)]:
			if cnd in weather_cnds.keys():
				conditions.append(weather_cnds[cnd])
			else:
				conditions.append(f"undef: {cnd}")

		return {
			"severity": severity,
			"condition": tuple(conditions)
		}

	@staticmethod
	def parse_runway_pressure(datablock):
		datablock = datablock[3:]
		pressures = datablock.split("/")
		pres = {
			"inHg": int(pressures[0]),
			"mPa": int(pressures[1]) if len(pressures) > 1 else None
		}
		return pres

	@staticmethod
	def parse_runway_remark(datablock):
		runway_callcode, runway_winddata = datablock.split("/")
		return {
			"id": runway_callcode,
			"wind_from": int(runway_winddata[:3]),
			"wind_speed": int(runway_winddata[3:5]),
			"wind_units": runway_winddata[5:]
		}

	def parse_metar(self, json_data):
		metar_data = json_data["metar"].split("\n")[1].split(" ")
		data = {}

		for datablock in metar_data:
			# callcode only
			if re.match(r"\b[a-zA-Z]{4}\b", datablock):
				data["callcode"] = datablock
			# time
			elif re.match(r"\b\d{6}[A-Z]\b", datablock):
				data["time"] = self.parse_time(datablock)
			# wind 1
			elif re.match(r"\b\d{5}[A-Z]{3}\b", datablock):
				data["wind"] = self.parse_wind(datablock, 0)
			# wind 2 (gusts)
			elif re.match(r"\b\d{5}G\d{2}[A-Z]{3}\b", datablock):
				data["wind"] = self.parse_wind(datablock, 1)
			# wind 3 (changes heading)
			elif re.match(r"\b\d{3}V\d{3}\b", datablock):
				if "wind" not in data.keys():
					data["wind"] = {}
				data["wind"] |= self.parse_wind(datablock, 2)
			# wind 4 (massively changes heading)
			elif re.match(r"\bVRB\d{2}.{3}\b", datablock):
				data["wind"] = self.parse_wind(datablock, 3)
			# weather
			elif re.search(regex_weather, datablock):
				data["weather"] = self.parse_weather(datablock)
			# visibility distance
			elif re.match(r"\b\d{4}\b", datablock):
				data["visibility_distance"] = self.parse_vd(datablock)
			# visibility in heading
			elif re.match(r"\b\d{4}?(NW|NE|SW|SE|W|N|S|E)\b", datablock):
				if "visibility_at" not in data.keys():
					data["visibility_at"] = []
				data["visibility_at"].append(self.parse_visibility_at(datablock))
			# cloudiness
			elif re.match(r"\b(CLR|FEW|SCT|BKN|OVC|CAVOK|NSC)(\d{3})?\b", datablock):
				if "clouds" not in data.keys(): 
					data["clouds"] = []
				data["clouds"].append(self.parse_clouds(datablock))
			# temperature
			elif re.match(r"\bM?\d{2}\/M?\d{2}\b", datablock):
				data["temperatures"] = self.parse_temperatures(datablock)
			# pressure
			elif re.match(r"\bQ\d{4}\b", datablock):
				data["pressure"] = self.parse_pressure(datablock)
			# runway statuses
			elif re.match(r"R\d{2}(R|L|C|)\/((\d|\/){6}|(CLRD|CLSD|SNOKLO))(\d{2})?", datablock):
				if "runways" not in data.keys():
					data["runways"] = []
				data["runways"].append(self.parse_runway(datablock))
			# runway remark (wind)
			elif re.match(r"\bR\d{2}(R|L|C|)\/\d{5}MPS\b", datablock):
				if "runway_remarks" not in data.keys():
					data["runway_remarks"] = []
				data["runway_remarks"].append(self.parse_runway_remark(datablock))
			# weather trends
			elif re.match(r"\b(NOSIG|TEMPO|BECMG)\b", datablock):
				data["trend"] = self.parse_trend(datablock)
			# remarks
			elif re.match(r"\bRMK\b", datablock):
				data["has_remarks"] = True
			# pressure at runways
			elif re.match(r"\bQFE\d{3}(\/\d{4}\b)?", datablock):
				data["pressure_at_runways"] = self.parse_runway_pressure(datablock)
			else:
				raise Exception(f"Nothing hit at {datablock}?")


		return data