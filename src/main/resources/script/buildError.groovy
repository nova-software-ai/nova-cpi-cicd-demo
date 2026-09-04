import com.sap.gateway.ip.core.customdev.util.Message
import groovy.json.JsonOutput

/*
 * Exception subprocess — build a clean, structured error response and set the
 * appropriate HTTP status. Never leaks stack traces. Maps by stage when the
 * error was not explicitly classified upstream.
 */
def Message processData(Message message) {
    def stage  = (message.getProperty("stage") ?: "UNKNOWN").toString()
    def code, status, msg

    // The caught exception is the authoritative signal: property writes made in a
    // script that then throws are discarded, so we classify from the exception text
    // (validation / not-found) and fall back to the last persisted stage otherwise.
    def ex = message.getProperty("CamelExceptionCaught")
    def exMsg = (ex != null && ex.getMessage() != null) ? ex.getMessage() : (ex != null ? ex.toString() : "")
    def exLow = exMsg.toLowerCase()
    def isTimeout = exLow.contains("timed out") || exLow.contains("timeout") || exLow.contains("sockettimeout")

    if (exMsg.contains("INVALID_ZIP")) {
        code = "INVALID_ZIP"; status = "400"; msg = "Enter a valid 5-digit US ZIP code."
    } else if (exMsg.contains("ZIP_NOT_FOUND")) {
        code = "ZIP_NOT_FOUND"; status = "404"; msg = "No location found for that ZIP."
    } else if (isTimeout && (stage == "WEATHER" || stage == "AIR" || stage == "GEOCODE")) {
        code = "UPSTREAM_TIMEOUT"; status = "504"; msg = "Upstream data source timed out."
    } else {
        switch (stage) {
            case "GEOCODE": code = "ZIP_NOT_FOUND";      status = "404"; msg = "No location found for that ZIP."; break
            case "WEATHER": code = "WEATHER_UPSTREAM";   status = "502"; msg = "Weather source unavailable.";     break
            case "AIR":     code = "AIRQUALITY_UPSTREAM";status = "502"; msg = "Air-quality source unavailable."; break
            case "MERGE":   code = "MERGE_FAILED";       status = "500"; msg = "Failed to merge results.";        break
            default:        code = "INTERNAL_ERROR";     status = "500"; msg = "Unexpected error.";               break
        }
    }

    def out = JsonOutput.toJson([error: code, message: msg])
    message.setBody(out)
    message.setHeader("Content-Type", "application/json")
    message.setHeader("CamelHttpResponseCode", Integer.parseInt(status.toString()))
    return message
}
