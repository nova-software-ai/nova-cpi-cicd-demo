import com.sap.gateway.ip.core.customdev.util.Message
import groovy.json.JsonOutput

/*
 * Exception Subprocess - log the error and build a clean JSON error response.
 *   "[CODE|status] text" anywhere in the cause chain -> that code/status (400 INVALID_REQUEST, 404 CITY_NOT_FOUND)
 *   HTTP / connection failure while calling Open-Meteo -> 502 UPSTREAM_ERROR
 *   anything else -> 500 INTERNAL_ERROR
 * The root cause (exception chain + downstream status/body) is always written to the MPL
 * as attachment "Error detail" and as custom header properties, independent of LOG_PAYLOADS.
 */
def Message processData(Message message) {
    def ex = message.getProperty('CamelExceptionCaught')
    String code = null, status = null, text = null

    for (def t = ex; t != null; t = t.getCause()) {
        def m = (t.getMessage() ?: '') =~ /\[([A-Z_]+)\|(\d{3})\]\s*([^@]*)/
        if (m.find()) { code = m.group(1); status = m.group(2); text = m.group(3).trim(); break }
        if (t.getCause() == t) break
    }

    String step = message.getProperty('currentStep') as String
    Integer upstreamStatus = null
    String upstreamBody = null
    String upstreamUri = null
    if (!code) {
        String exName = ex?.getClass()?.getName() ?: ''
        boolean upstream = step && (exName.contains('Http') || exName.contains('Ahc') || exName.contains('Timeout')
                || exName.contains('Connect') || exName.contains('UnknownHost') || exName.contains('Socket') || exName.contains('SSL'))
        try { upstreamStatus = ex.getStatusCode() as Integer } catch (ignored) { }
        try { upstreamBody = ex.getResponseBody() as String } catch (ignored) { }
        try { upstreamUri = ex.getUri() as String } catch (ignored) { }
        if (upstream) {
            code = 'UPSTREAM_ERROR'; status = '502'
            text = "Open-Meteo ${step} call failed" + (upstreamStatus ? " (HTTP ${upstreamStatus})" : '') + '.'
        } else {
            code = 'INTERNAL_ERROR'; status = '500'
            text = 'Unexpected error while processing the request.'
        }
    }

    // Root cause chain for the MPL
    StringBuilder sb = new StringBuilder()
    sb << "errorCode: ${code}\nhttpStatus: ${status}\nfailedStep: ${step ?: 'n/a'}\n"
    if (upstreamStatus) sb << "downstreamStatus: ${upstreamStatus}\n"
    if (upstreamUri) sb << "downstreamUri: ${upstreamUri.replaceAll(/\?.*/, '?…')}\n"
    if (upstreamBody) sb << "downstreamBody: ${upstreamBody.take(2000)}\n"
    sb << 'exceptionChain:\n'
    int depth = 0
    def cur = ex
    while (cur != null && depth < 10) {
        sb << "  [${depth}] ${cur.getClass().getName()}: ${cur.getMessage()}\n"
        if (cur.getCause() == cur) break
        cur = cur.getCause()
        depth++
    }

    def log = messageLogFactory.getMessageLog(message)
    log?.addCustomHeaderProperty('errorCode', code)
    log?.addCustomHeaderProperty('httpStatus', status)
    if (step) log?.addCustomHeaderProperty('failedStep', step)
    if (upstreamStatus) log?.addCustomHeaderProperty('downstreamStatus', upstreamStatus.toString())
    log?.setStringProperty('rootCause', (ex?.getClass()?.getSimpleName() ?: '') + ': ' + (ex?.getMessage() ?: '').take(300))
    log?.addAttachmentAsString('Error detail', sb.toString(), 'text/plain')

    String mplId = message.getProperty('SAP_MessageProcessingLogID') as String
    message.setBody(JsonOutput.prettyPrint(JsonOutput.toJson([error: [code: code, status: status as Integer, message: text, messageProcessingLogId: mplId]])))
    message.setHeaders([:])
    message.setHeader('Content-Type', 'application/json; charset=utf-8')
    message.setHeader('CamelHttpResponseCode', status as Integer)
    return message
}
