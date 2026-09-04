import com.sap.gateway.ip.core.customdev.util.Message
import groovy.json.JsonSlurper

/*
 * Step 5 — Extract coordinates from the Zippopotam geocode response.
 * Sets lat/lon/placeName/state/stateAbbr properties, validates that a place
 * was returned (empty -> ZIP_NOT_FOUND), and prepares the weather URL.
 */
def Message processData(Message message) {
    message.setProperty("stage", "GEOCODE")
    def body = (message.getBody(java.lang.String) ?: "").toString()

    def json = null
    try {
        json = new JsonSlurper().parseText(body)
    } catch (e) {
        json = null
    }

    def places = (json != null && json.places instanceof List) ? json.places : []
    if (places == null || places.size() == 0) {
        message.setProperty("errorCode", "ZIP_NOT_FOUND")
        message.setProperty("httpStatus", "404")
        message.setProperty("errorMessage", "No location found for that ZIP.")
        throw new RuntimeException("ZIP_NOT_FOUND")
    }

    def p0 = places[0]
    def lat = (p0.latitude ?: "").toString().trim()
    def lon = (p0.longitude ?: "").toString().trim()
    message.setProperty("lat", lat)
    message.setProperty("lon", lon)
    message.setProperty("placeName", (p0["place name"] ?: "").toString())
    message.setProperty("state", (p0.state ?: "").toString())
    message.setProperty("stateAbbr", (p0["state abbreviation"] ?: "").toString())

    def q = "latitude=" + lat +
            "&longitude=" + lon +
            "&current=temperature_2m,relative_humidity_2m,apparent_temperature,is_day,precipitation,weather_code,wind_speed_10m" +
            "&temperature_unit=fahrenheit&wind_speed_unit=mph"
    def weatherBase = "https://api.open-meteo.com/v1/forecast"
    message.setProperty("weatherUrl", weatherBase)   // base URL only; query goes in CamelHttpQuery
    message.setHeader("CamelHttpUri", weatherBase)
    message.setHeader("CamelHttpQuery", q)
    message.setProperty("stage", "WEATHER")
    message.setBody("")
    return message
}
