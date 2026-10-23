import com.sap.gateway.ip.core.customdev.util.Message
import groovy.json.JsonSlurper

/*
 * Parse request (v2) - reads the lookup parameters from the query string (GET) or a JSON body (POST)
 * and decides whether the city must be geocoded first.
 *
 *   city + country (optional ISO-3166 alpha-2)  OR  lat + lon ;  units = metric (default) | imperial
 *
 * v2 change: this step no longer builds the forecast query. It only sets latitude/longitude;
 * the query is built once, in BuildForecastQuery.groovy, for both routes.
 * Validation errors are thrown as "[CODE|status] text" and mapped by the Exception Subprocess.
 */
def Message processData(Message message) {
    Map<String, String> p = [:]

    String query = message.getHeaders().get('CamelHttpQuery') as String
    if (query) {
        query.split('&').each { pair ->
            if (!pair) return
            def kv = pair.split('=', 2)
            String key = URLDecoder.decode(kv[0], 'UTF-8').toLowerCase()
            p[key] = (kv.length > 1 ? URLDecoder.decode(kv[1], 'UTF-8') : '').trim()
        }
    }

    String body = message.getBody(String)
    if (body?.trim()?.startsWith('{')) {
        try {
            new JsonSlurper().parseText(body).each { k, v -> if (v != null) p[k.toString().toLowerCase()] = v.toString().trim() }
        } catch (Exception e) {
            throw new IllegalArgumentException('[INVALID_REQUEST|400] Request body is not valid JSON.')
        }
    }

    String units = (p.units ?: 'metric').toLowerCase()
    if (!(units in ['metric', 'imperial'])) {
        throw new IllegalArgumentException("[INVALID_REQUEST|400] Invalid units '${units}'. Use 'metric' or 'imperial'.")
    }
    message.setProperty('units', units)

    String lat = p.lat ?: p.latitude
    String lon = p.lon ?: p.longitude
    String city = p.city ?: p.name

    if (lat && lon) {
        if (!(lat ==~ /-?\d+(\.\d+)?/) || !(lon ==~ /-?\d+(\.\d+)?/)) {
            throw new IllegalArgumentException('[INVALID_REQUEST|400] lat and lon must be decimal numbers.')
        }
        message.setProperty('needGeocode', 'false')
        message.setProperty('locationName', city ?: "${lat},${lon}")
        message.setProperty('locationCountry', p.country ?: '')
        message.setProperty('locationRegion', '')
        message.setProperty('latitude', lat)
        message.setProperty('longitude', lon)
    } else if (city) {
        String q = "name=${URLEncoder.encode(city, 'UTF-8')}&count=1&language=en&format=json"
        if (p.country) q += "&countryCode=${URLEncoder.encode(p.country.toUpperCase(), 'UTF-8')}"
        message.setProperty('needGeocode', 'true')
        message.setProperty('requestedCity', city)
        message.setProperty('requestedCountry', p.country ?: '')
        message.setProperty('geoQuery', q)
        message.setProperty('currentStep', 'Geocoding')
    } else {
        throw new IllegalArgumentException("[INVALID_REQUEST|400] Provide either 'city' (optionally with 'country') or 'lat' and 'lon'.")
    }

    def log = messageLogFactory.getMessageLog(message)
    log?.addCustomHeaderProperty('city', city ?: '')
    log?.addCustomHeaderProperty('country', p.country ?: '')

    // Do not let the inbound HTTP details leak into the outbound HTTP calls.
    ['CamelHttpQuery', 'CamelHttpPath', 'CamelHttpUri', 'CamelHttpUrl', 'CamelServletContextPath'].each { message.headers.remove(it) }
    message.setBody('')
    return message
}
