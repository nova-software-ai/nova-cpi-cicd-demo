import com.sap.gateway.ip.core.customdev.util.Message

/*
 * Build forecast query (v2, new) - the single place where the Open-Meteo forecast query is built.
 * Both routes (coordinates given / city geocoded) converge on this step, so the field list
 * and unit handling exist exactly once.
 */
def Message processData(Message message) {
    String lat = message.getProperty('latitude') as String
    String lon = message.getProperty('longitude') as String
    String units = (message.getProperty('units') ?: 'metric') as String

    String q = "latitude=${lat}&longitude=${lon}" +
            '&current=temperature_2m,relative_humidity_2m,apparent_temperature,weather_code,wind_speed_10m' +
            '&timezone=auto'
    if (units == 'imperial') q += '&temperature_unit=fahrenheit&wind_speed_unit=mph'

    message.setProperty('forecastQuery', q)
    message.setProperty('currentStep', 'Forecast')
    message.setBody('')
    return message
}
