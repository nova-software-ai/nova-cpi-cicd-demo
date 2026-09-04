import com.sap.gateway.ip.core.customdev.util.Message

/*
 * Step 2 — Init & validate.
 * Reads query param 'zip' from CamelHttpQuery, defaults to 90210 when absent,
 * validates ^\d{5}$, captures requestReceivedAt, and prepares the geocode URL.
 */
def Message processData(Message message) {
    def query = (message.getHeaders().get("CamelHttpQuery") ?: "").toString()
    def zip = null
    query.split("&").each { pair ->
        def kv = pair.split("=", 2)
        if (kv.length == 2 && kv[0] == "zip") {
            zip = java.net.URLDecoder.decode(kv[1], "UTF-8")
        }
    }
    if (zip == null || zip.trim().isEmpty()) {
        zip = (message.getProperty("defaultZip") ?: "90210").toString()   // externalized configuration parameter
    }
    zip = zip.trim()

    def sdf = new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss'Z'")
    sdf.setTimeZone(java.util.TimeZone.getTimeZone("UTC"))
    message.setProperty("requestReceivedAt", sdf.format(new java.util.Date()))
    message.setProperty("stage", "GEOCODE")
    message.setProperty("startedAtMs", String.valueOf(System.currentTimeMillis()))

    if (!(zip ==~ /^\d{5}$/)) {
        message.setProperty("errorCode", "INVALID_ZIP")
        message.setProperty("httpStatus", "400")
        message.setProperty("errorMessage", "Enter a valid 5-digit US ZIP code.")
        throw new RuntimeException("INVALID_ZIP: " + zip)
    }

    message.setProperty("zip", zip)
    def geoUrl = "https://api.zippopotam.us/us/" + zip
    message.setProperty("geoUrl", geoUrl)
    message.setHeader("CamelHttpUri", geoUrl)   // dynamic address for the geocode receiver
    message.setBody("")
    return message
}
