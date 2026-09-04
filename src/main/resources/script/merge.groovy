import com.sap.gateway.ip.core.customdev.util.Message
import groovy.json.JsonSlurper
import groovy.json.JsonOutput

/*
 * Step 8 — Merge & normalize geocode + weather + air-quality into the schema
 * from the tech spec (section 3.5). Handles numeric edge cases explicitly:
 * weather_code == 0 is valid ("Clear sky"), precipitation/us_aqi/is_day == 0 are valid.
 */

def wmoText(Integer code) {
    def map = [
        0:"Clear sky",
        1:"Mainly clear", 2:"Partly cloudy", 3:"Overcast",
        45:"Fog", 48:"Depositing rime fog",
        51:"Light drizzle", 53:"Moderate drizzle", 55:"Dense drizzle",
        56:"Light freezing drizzle", 57:"Dense freezing drizzle",
        61:"Slight rain", 63:"Moderate rain", 65:"Heavy rain",
        66:"Light freezing rain", 67:"Heavy freezing rain",
        71:"Slight snowfall", 73:"Moderate snowfall", 75:"Heavy snowfall",
        77:"Snow grains",
        80:"Slight rain showers", 81:"Moderate rain showers", 82:"Violent rain showers",
        85:"Slight snow showers", 86:"Heavy snow showers",
        95:"Thunderstorm",
        96:"Thunderstorm with slight hail", 99:"Thunderstorm with heavy hail"
    ]
    return map.containsKey(code) ? map[code] : ("Unknown (code " + code + ")")
}

def aqiCategory(Integer aqi) {
    if (aqi == null) return "Unknown"
    if (aqi <= 50)  return "Good"
    if (aqi <= 100) return "Moderate"
    if (aqi <= 150) return "Unhealthy for Sensitive Groups"
    if (aqi <= 200) return "Unhealthy"
    if (aqi <= 300) return "Very Unhealthy"
    return "Hazardous"
}

def asNum(v) {
    if (v == null) return null
    try { return new java.math.BigDecimal(v.toString()) } catch (e) { return null }
}

def buildOutput(Message message) {
    def slurper = new JsonSlurper()

    def wRoot = slurper.parseText((message.getProperty("weatherJson") ?: "{}").toString())
    def aRoot = slurper.parseText((message.getBody(java.lang.String) ?: "{}").toString())

    def wCur   = (wRoot?.current ?: [:])
    def wUnits = (wRoot?.current_units ?: [:])
    def aCur   = (aRoot?.current ?: [:])
    def aUnits = (aRoot?.current_units ?: [:])

    Integer wcode = wCur.containsKey("weather_code") ? (wCur.weather_code as Integer) : null
    Integer usAqi = aCur.containsKey("us_aqi") ? (aCur.us_aqi as Integer) : null

    def windUnit = (wUnits.wind_speed_10m ?: "mph").toString().replace("mp/h", "mph")
    def tempUnit = (wUnits.temperature_2m ?: "\u00b0F").toString()

    def wTime = wCur.time ? (wCur.time.toString() + "Z") : null
    def aTime = aCur.time ? (aCur.time.toString() + "Z") : null

    def isoNow = new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")
    isoNow.setTimeZone(java.util.TimeZone.getTimeZone("UTC"))

    def out = [
        location: [
            zip              : message.getProperty("zip"),
            city             : message.getProperty("placeName"),
            state            : message.getProperty("state"),
            stateAbbreviation: message.getProperty("stateAbbr"),
            latitude         : asNum(message.getProperty("lat")),
            longitude        : asNum(message.getProperty("lon"))
        ],
        weather: [
            temperature        : wCur.temperature_2m,
            temperatureUnit    : tempUnit,
            apparentTemperature: wCur.apparent_temperature,
            humidityPct        : wCur.relative_humidity_2m,
            windSpeed          : wCur.wind_speed_10m,
            windSpeedUnit      : windUnit,
            precipitation      : wCur.precipitation,
            isDay              : (wCur.containsKey("is_day") ? (wCur.is_day == 1) : null),
            weatherCode        : wcode,
            condition          : (wcode != null ? wmoText(wcode) : "Unknown"),
            observedAt         : wTime
        ],
        airQuality: [
            usAqi          : usAqi,
            category       : aqiCategory(usAqi),
            pm2_5          : aCur.pm2_5,
            pm10           : aCur.pm10,
            ozone          : aCur.ozone,
            nitrogenDioxide: aCur.nitrogen_dioxide,
            sulphurDioxide : aCur.sulphur_dioxide,
            carbonMonoxide : aCur.carbon_monoxide,
            unit           : (aUnits.pm2_5 ?: "\u03bcg/m\u00b3").toString(),
            observedAt     : aTime
        ],
        sources: [
            [name: "Zippopotam.us", purpose: "geocoding"],
            [name: "Open-Meteo",    purpose: "weather"],
            [name: "Open-Meteo Air Quality", purpose: "air quality"]
        ],
        generatedAt: isoNow.format(new java.util.Date()),
        dataQuality: [
            completeness   : (wCur != null && aCur != null) ? "COMPLETE" : "PARTIAL",
            weatherPresent : (wCur != null),
            airQualityPresent : (aCur != null),
            latencyMs      : (System.currentTimeMillis() - Long.parseLong(
                                 (message.getProperty("startedAtMs") ?: String.valueOf(System.currentTimeMillis())).toString()))
        ]
    ]

    message.setBody(JsonOutput.toJson(out))
    message.setHeader("Content-Type", "application/json")
    message.setHeader("CamelHttpResponseCode", 200)
    return message
}

def Message processData(Message message) {
    message.setProperty("stage", "MERGE")
    try {
        return buildOutput(message)
    } catch (Exception e) {
        // Self-contained failure handling: return a clean 500 without leaking traces.
        message.setBody(JsonOutput.toJson([error: "MERGE_FAILED", message: "Failed to merge results."]))
        message.setHeader("Content-Type", "application/json")
        message.setHeader("CamelHttpResponseCode", 500)
        return message
    }
}
