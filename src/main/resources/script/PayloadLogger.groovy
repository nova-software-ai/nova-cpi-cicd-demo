import com.sap.gateway.ip.core.customdev.util.Message

/*
 * Payload logger (v2, new) - writes MPL attachments at three points of the flow.
 * Switched by the externalized parameter LOG_PAYLOADS (copied to property 'logPayloads'
 * by the "Read configuration" Content Modifier). Off = no attachments, no overhead.
 *
 * One script, three entry points (selected per step via the "Script Function" setting):
 *   logRequest     - inbound request (query string + body)
 *   logDownstream  - Open-Meteo response of the call just made (geocoding or forecast)
 *   logOutput      - final mapped output returned to the caller
 * The body is never changed.
 */
def Message logRequest(Message message) {
    String query = message.getHeaders().get('CamelHttpQuery') as String
    String method = message.getHeaders().get('CamelHttpMethod') as String
    attach(message, '01 Request in', "method: ${method ?: ''}\nquery: ${query ?: ''}\nbody:\n${message.getBody(String) ?: ''}", 'text/plain')
    return message
}

def Message logDownstream(Message message) {
    String step = (message.getProperty('currentStep') ?: 'Downstream') as String
    String code = message.getHeaders().get('CamelHttpResponseCode') as String
    attach(message, "02 Downstream response - ${step}" + (code ? " (HTTP ${code})" : ''), message.getBody(String) ?: '', 'application/json')
    return message
}

def Message logOutput(Message message) {
    attach(message, '03 Final output', message.getBody(String) ?: '', 'application/json')
    return message
}

private void attach(Message message, String name, String content, String type) {
    if (!'true'.equalsIgnoreCase((message.getProperty('logPayloads') ?: 'false') as String)) return
    def log = messageLogFactory.getMessageLog(message)
    log?.addAttachmentAsString(name, content, type)
}
