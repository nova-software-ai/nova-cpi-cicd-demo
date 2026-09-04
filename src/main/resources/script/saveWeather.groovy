import com.sap.gateway.ip.core.customdev.util.Message

/*
 * Step 6/7 bridge — capture the weather response into a property (before the
 * air-quality call overwrites the message body) and prepare the air-quality URL.
 */
def Message processData(Message message) {
    def body = (message.getBody(java.lang.String) ?: "").toString()
    message.setProperty("weatherJson", body)

    def lat = message.getProperty("lat")
    def lon = message.getProperty("lon")
    def airBase = "https://air-quality-api.open-meteo.com/v1/air-quality"
    def airQuery = "latitude=" + lat +
                   "&longitude=" + lon +
                   "&current=us_aqi,pm10,pm2_5,ozone,nitrogen_dioxide,sulphur_dioxide,carbon_monoxide"
    message.setProperty("airUrl", airBase)   // base URL only; query goes in CamelHttpQuery
    message.setHeader("CamelHttpUri", airBase)
    message.setHeader("CamelHttpQuery", airQuery)
    message.setProperty("stage", "AIR")
    message.setBody("")
    return message
}
