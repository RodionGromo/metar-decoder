import datetime, requests

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

def parse(json_data):
    raw_date, raw_data, _ = json_data["metar"].split("\n")
    report_date = datetime.datetime.strptime(raw_date, "%Y-%m-%d %H:%M:%S")

    raw_data = raw_data.split(" ")
    data = dict()
    data["callcode"] = raw_data[0]
    data["datetime"] = datetime.datetime.strptime(raw_data[1][:-1], "%d%H%M")
    data["wind_angle"] = int(raw_data[2][:3])
    data["wind_speed"] = str(int(raw_data[2][3:5])) + " " + raw_data[2][5:]
    data["visibility_distance"] = int(raw_data[3])
    # weather
    weather_status = ["medium", ""]
    raw_weather_status = raw_data[4]
    if raw_weather_status[0] in ["-", "+"]:
        if raw_weather_status[0] == "-":
            weather_status[0] = "light"
        else:
            weather_status[0] = "heavy"
        for stat in [raw_weather_status[i:i+2] for i in range(1, len(raw_weather_status), 2)]:
            if(stat in weather_cnds.keys()):
                weather_status[1] += weather_cnds[stat] + " "
    else:
        for stat in [raw_weather_status[i:i+2] for i in range(0, len(raw_weather_status), 2)]:
            if(stat in weather_cnds.keys()):
                weather_status[1] += weather_cnds[stat] + " "
    data["weather_status"] = " ".join(weather_status)

    #cloudiness (can be more than one)
    i = 5
    data["cloudiness"] = ""
    while True:
        raw_cloudiness = raw_data[i]
        cloudiness = ""
        cl_stat = raw_cloudiness[:3]
        if cl_stat in cloud_cnds.keys():
            cloudiness += cloud_cnds[cl_stat]
        else:
            break
        cloudiness += " at height "
        cloudiness += str(int(raw_cloudiness[3:6]) * 100) + "ft"
        additional_data = raw_cloudiness[6:]
        if additional_data in cloud_cnds2.keys():
            cloudiness += " " + cloud_cnds2[additional_data]
        elif additional_data != "":
            cloudiness += f" undefined cnd: {additional_data}"
        data["cloudiness"] += cloudiness + " | "
        i += 1
    # temperature
    air_temp, dew_temp = raw_data[i].split("/")
    if("M" in air_temp):
        data["air_temp"] = str(-int(air_temp[1:]))
    else:
        data["air_temp"] = str(int(air_temp))
    data["air_temp"] += " celsius"

    if("M" in dew_temp):
        data["dew_temp"] = str(-int(dew_temp[1:]))
    else:
        data["dew_temp"] = str(int(dew_temp))
    data["dew_temp"] += " celsius"
    
    # pressure
    i+=1
    pressure_data = raw_data[i]
    data["pressure"] = str(int(pressure_data[1:]))
    if pressure_data[0] == "Q":
    	data["pressure"] += " hPa"
    elif pressure_data[0] == "A":
    	data["pressure"] += " inHg"
    return (report_date, data)


ask = "uuob"
json_data = requests.get(f"https://metartaf.ru/{ask.upper()}.json").json()

print(json_data["metar"])
date, data = parse(json_data)
print("report date:",date)
print("report:")
for key, value in data.items():
    print(f"{key}: {value}")


