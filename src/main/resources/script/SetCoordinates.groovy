import com.sap.gateway.ip.core.customdev.util.Message
import groovy.json.JsonSlurper

/*
 * Set coordinates (v2) - takes the first hit of the Open-Meteo geocoding response.
 * v2 change: no longer builds the forecast query (that was a copy of the code in PrepareRequest);
 * it only sets the location properties. An empty result is a clean 404, not a generic 500.
 */
def Message processData(Message message) {
    def geo = new JsonSlurper().parseText(message.getBody(String) ?: '{}')
    def hit = geo.results ? geo.results[0] : null
    if (!hit) {
        String city = message.getProperty('requestedCity')
        String country = message.getProperty('requestedCountry')
        throw new IllegalArgumentException("[CITY_NOT_FOUND|404] City '${city}'" + (country ? " (country ${country})" : '') + ' was not found.')
    }

    message.setProperty('locationName', hit.name ?: '')
    message.setProperty('locationCountry', hit.country_code ?: '')
    message.setProperty('locationRegion', hit.admin1 ?: '')
    message.setProperty('latitude', hit.latitude.toString())
    message.setProperty('longitude', hit.longitude.toString())
    message.setBody('')
    return message
}
