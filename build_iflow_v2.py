"""Generates the Weather_Data_v2 iFlow (BPMN .iflw + bundle files) and zips it for upload to SAP Cloud Integration.

Changes vs. Weather_Data (see CHANGES.md):
  * Open-Meteo URLs, timeout and payload-logging switch externalized ({{...}} parameters)
  * forecast query built once (BuildForecastQuery.groovy) instead of twice
  * Open-Meteo response mapped by JSON->XML converter + XSLT (WeatherReport.xsl) + XML->JSON converter
  * Exception Subprocess with clean JSON errors (400/404/502/500), returnExceptionToSender=false
  * MPL payload attachments (PayloadLogger.groovy) switched by LOG_PAYLOADS
"""
import os, sys, zipfile
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _helpers import props, request_reply, seq, manifest, IFLOW_ID, IFLOW_NAME

ROOT = os.path.dirname(os.path.abspath(__file__))
URL_PATH = '/weather-v2'

PARAMS = {  # name -> (default, description)
    'GEOCODING_URL': ('https://geocoding-api.open-meteo.com/v1/search', 'Open-Meteo geocoding endpoint'),
    'FORECAST_URL': ('https://api.open-meteo.com/v1/forecast', 'Open-Meteo forecast endpoint'),
    'HTTP_TIMEOUT_MS': ('60000', 'Timeout for the Open-Meteo calls (ms)'),
    'LOG_PAYLOADS': ('true', 'true = write request/downstream/output payloads as MPL attachments'),
}


def ins_outs(incoming, outgoing):
    return ''.join(f'<bpmn2:incoming>{i}</bpmn2:incoming>' for i in incoming) + \
        ''.join(f'<bpmn2:outgoing>{o}</bpmn2:outgoing>' for o in outgoing)


def http_receiver(flow_id, name, source, target, url, query):
    return f'<bpmn2:messageFlow id="{flow_id}" name="HTTP" sourceRef="{source}" targetRef="{target}">' + props({
        'Description': f'Call {name}', 'methodSourceExpression': '', 'ComponentNS': 'sap', 'privateKeyAlias': '',
        'httpMethod': 'GET', 'Name': 'HTTP', 'TransportProtocolVersion': '1.7.2', 'ComponentSWCVName': 'external',
        'proxyPort': '', 'httpAddressQuery': query, 'httpRequestTimeout': '{{HTTP_TIMEOUT_MS}}', 'MessageProtocol': 'None',
        'ComponentSWCVId': '1.7.2', 'direction': 'Receiver', 'ComponentType': 'HTTP', 'httpShouldSendBody': 'false',
        'proxyType': 'default', 'componentVersion': '1.7', 'proxyHost': '', 'system': name,
        'authenticationMethod': 'None', 'locationID': '', 'TransportProtocol': 'HTTP', 'throwExceptionOnFailure': 'true',
        'cmdVariantUri': 'ctype::AdapterVariant/cname::sap:HTTP/tp::HTTP/mp::None/direction::Receiver/version::1.7.2',
        'credentialName': '', 'MessageProtocolVersion': '1.7.2', 'httpAddressWithoutQuery': url,
    }) + '</bpmn2:messageFlow>'


def script(step_id, name, file, incoming, outgoing, function=''):
    return f'<bpmn2:callActivity id="{step_id}" name="{name}">' + props({
        'scriptFunction': function, 'componentVersion': '1.0', 'activityType': 'Script',
        'cmdVariantUri': 'ctype::FlowstepVariant/cname::GroovyScript/version::1.0.1',
        'subActivityType': 'GroovyScript', 'script': file,
    }) + ins_outs(incoming, outgoing) + '</bpmn2:callActivity>'


def row(name, value, typ='constant', datatype=''):
    return (f"<row><cell id='Action'>Create</cell><cell id='Type'>{typ}</cell><cell id='Value'>{value}</cell>"
            f"<cell id='Default'></cell><cell id='Name'>{name}</cell><cell id='Datatype'>{datatype}</cell></row>")


def content_modifier(step_id, name, incoming, outgoing, properties=None, headers=None):
    p = {'bodyType': 'expression', 'componentVersion': '1.6', 'activityType': 'Enricher',
         'cmdVariantUri': 'ctype::FlowstepVariant/cname::Enricher/version::1.6.5'}
    if properties:
        p['propertyTable'] = ''.join(row(*r) for r in properties)
    if headers:
        p['headerTable'] = ''.join(row(*r) for r in headers)
    return f'<bpmn2:callActivity id="{step_id}" name="{name}">' + props(p) + ins_outs(incoming, outgoing) + '</bpmn2:callActivity>'


def json_to_xml(step_id, name, incoming, outgoing):
    return f'<bpmn2:callActivity id="{step_id}" name="{name}">' + props({
        'additionalRootElementName': 'root', 'componentVersion': '1.1', 'activityType': 'JsonToXmlConverter',
        'cmdVariantUri': 'ctype::FlowstepVariant/cname::JsonToXmlConverter/version::1.1.2',
        'useNamespaces': 'false', 'addXMLRootElement': 'true', 'jsonNamespaceSeparator': ':',
    }) + ins_outs(incoming, outgoing) + '</bpmn2:callActivity>'


def xml_to_json(step_id, name, incoming, outgoing):
    return f'<bpmn2:callActivity id="{step_id}" name="{name}">' + props({
        'xmlJsonUseStreaming': 'false', 'xmlJsonSuppressRootElement': 'true', 'componentVersion': '1.0',
        'xmlJsonConvertAllElements': 'specific', 'activityType': 'XmlToJsonConverter',
        'cmdVariantUri': 'ctype::FlowstepVariant/cname::XmlToJsonConverter/version::1.0.8',
        'useNamespaces': 'false', 'jsonNamespaceSeparator': ':',
    }) + ins_outs(incoming, outgoing) + '</bpmn2:callActivity>'


def xslt(step_id, name, mapping, incoming, outgoing):
    return f'<bpmn2:callActivity id="{step_id}" name="{name}">' + props({
        'mappingoutputformat': 'Bytes', 'mappinguri': f'dir://mapping/xslt/src/main/resources/mapping/{mapping}.xsl',
        'mappingname': mapping, 'mappingpath': f'src/main/resources/mapping/{mapping}', 'mappingSource': 'mappingSrcIflow',
        'componentVersion': '1.2', 'activityType': 'Mapping',
        'cmdVariantUri': 'ctype::FlowstepVariant/cname::XSLTMapping/version::1.2.0', 'subActivityType': 'XSLTMapping',
    }) + ins_outs(incoming, outgoing) + '</bpmn2:callActivity>'


# ---------- layout (x, y, w, h) ----------
Y = 300
shapes = {
    'Participant_Sender': (20, 230, 100, 140),
    'Participant_Geocoding': (930, -170, 100, 140),
    'Participant_Forecast': (1390, -170, 100, 140),
    'Participant_Process_1': (160, 40, 2560, 560),
    'StartEvent_1': (200, Y + 14, 32, 32),
    'CA_Config': (270, Y, 100, 60),
    'CA_LogRequest': (410, Y, 100, 60),
    'CA_Prepare': (550, Y, 100, 60),
    'ExclusiveGateway_Geo': (700, Y + 10, 40, 40),
    'ST_Geocode': (930, 130, 100, 60),
    'CA_LogGeo': (1070, 130, 100, 60),
    'CA_SetCoords': (1210, 130, 100, 60),
    'CA_BuildQuery': (1250, Y, 100, 60),
    'ST_Forecast': (1390, Y, 100, 60),
    'CA_LogForecast': (1530, Y, 100, 60),
    'CA_JsonToXml': (1670, Y, 100, 60),
    'CA_Mapping': (1810, Y, 100, 60),
    'CA_XmlToJson': (1950, Y, 100, 60),
    'CA_Response': (2090, Y, 100, 60),
    'CA_LogOutput': (2230, Y, 100, 60),
    'EndEvent_1': (2400, Y + 14, 32, 32),
    'SubProcess_Error': (550, 420, 520, 150),
    'StartEvent_Error': (590, 479, 32, 32),
    'CA_Error': (750, 465, 100, 60),
    'EndEvent_Error': (970, 479, 32, 32),
}


def center(e):
    x, y, w, h = shapes[e]
    return x + w / 2, y + h / 2


chain = [  # main sequence (flow id, source, target)
    ('SF_1', 'StartEvent_1', 'CA_Config'),
    ('SF_2', 'CA_Config', 'CA_LogRequest'),
    ('SF_3', 'CA_LogRequest', 'CA_Prepare'),
    ('SF_4', 'CA_Prepare', 'ExclusiveGateway_Geo'),
    ('SF_City', 'ExclusiveGateway_Geo', 'ST_Geocode'),
    ('SF_Coords', 'ExclusiveGateway_Geo', 'CA_BuildQuery'),
    ('SF_5', 'ST_Geocode', 'CA_LogGeo'),
    ('SF_6', 'CA_LogGeo', 'CA_SetCoords'),
    ('SF_7', 'CA_SetCoords', 'CA_BuildQuery'),
    ('SF_8', 'CA_BuildQuery', 'ST_Forecast'),
    ('SF_9', 'ST_Forecast', 'CA_LogForecast'),
    ('SF_10', 'CA_LogForecast', 'CA_JsonToXml'),
    ('SF_11', 'CA_JsonToXml', 'CA_Mapping'),
    ('SF_12', 'CA_Mapping', 'CA_XmlToJson'),
    ('SF_13', 'CA_XmlToJson', 'CA_Response'),
    ('SF_14', 'CA_Response', 'CA_LogOutput'),
    ('SF_15', 'CA_LogOutput', 'EndEvent_1'),
    ('SF_E1', 'StartEvent_Error', 'CA_Error'),
    ('SF_E2', 'CA_Error', 'EndEvent_Error'),
]
edges = [('MessageFlow_Sender', 'Participant_Sender', 'StartEvent_1'),
         ('MessageFlow_Geocoding', 'ST_Geocode', 'Participant_Geocoding'),
         ('MessageFlow_Forecast', 'ST_Forecast', 'Participant_Forecast')] + chain

collab_props = props({
    'namespaceMapping': '', 'allowedHeaderList': '', 'httpSessionHandling': 'None', 'ServerTrace': 'false',
    'returnExceptionToSender': 'false', 'log': 'All events', 'componentVersion': '1.1',
    'cmdVariantUri': 'ctype::IFlowVariant/cname::IFlowConfiguration/version::1.1.15',
})

sender_flow = '<bpmn2:messageFlow id="MessageFlow_Sender" name="HTTPS" sourceRef="Participant_Sender" targetRef="StartEvent_1">' + props({
    'ComponentType': 'HTTPS', 'Description': 'Weather lookup endpoint (v2)', 'maximumBodySize': '40', 'ComponentNS': 'sap',
    'componentVersion': '1.3', 'urlPath': URL_PATH, 'Name': 'HTTPS', 'TransportProtocolVersion': '1.3.0',
    'ComponentSWCVName': 'external', 'system': 'Client', 'xsrfProtection': '0', 'TransportProtocol': 'HTTPS',
    'cmdVariantUri': 'ctype::AdapterVariant/cname::sap:HTTPS/tp::HTTPS/mp::None/direction::Sender/version::1.3.0',
    'userRole': 'ESBMessaging.send', 'senderAuthType': 'RoleBased', 'MessageProtocol': 'None',
    'MessageProtocolVersion': '1.3.0', 'ComponentSWCVId': '1.3.0', 'direction': 'Sender', 'clientCertificates': '',
}) + '</bpmn2:messageFlow>'


def participant(pid, ptype, name):
    return f'<bpmn2:participant id="{pid}" ifl:type="{ptype}" name="{name}">' + props({'ifl:type': ptype}) + '</bpmn2:participant>'


collaboration = (
    '<bpmn2:collaboration id="Collaboration_1" name="Default Collaboration">' + collab_props +
    participant('Participant_Sender', 'EndpointSender', 'Client') +
    participant('Participant_Geocoding', 'EndpointRecevier', 'OpenMeteo_Geocoding') +
    participant('Participant_Forecast', 'EndpointRecevier', 'OpenMeteo_Forecast') +
    '<bpmn2:participant id="Participant_Process_1" ifl:type="IntegrationProcess" name="Integration Process" processRef="Process_1"><bpmn2:extensionElements/></bpmn2:participant>' +
    sender_flow +
    http_receiver('MessageFlow_Geocoding', 'OpenMeteo_Geocoding', 'ST_Geocode', 'Participant_Geocoding',
                  '{{GEOCODING_URL}}', '${property.geoQuery}') +
    http_receiver('MessageFlow_Forecast', 'OpenMeteo_Forecast', 'ST_Forecast', 'Participant_Forecast',
                  '{{FORECAST_URL}}', '${property.forecastQuery}') +
    '</bpmn2:collaboration>'
)

exception_subprocess = (
    '<bpmn2:subProcess id="SubProcess_Error" name="Exception Subprocess">' + props({
        'componentVersion': '1.0', 'activityType': 'ErrorEventSubProcessTemplate',
        'cmdVariantUri': 'ctype::FlowstepVariant/cname::ErrorEventSubProcessTemplate/version::1.0.2'}) +
    '<bpmn2:startEvent id="StartEvent_Error" name="Error Start"><bpmn2:outgoing>SF_E1</bpmn2:outgoing><bpmn2:errorEventDefinition>' +
    props({'cmdVariantUri': 'ctype::FlowstepVariant/cname::ErrorStartEvent', 'activityType': 'StartErrorEvent'}) +
    '</bpmn2:errorEventDefinition></bpmn2:startEvent>' +
    script('CA_Error', 'Log error and build error response', 'BuildErrorResponse.groovy', ['SF_E1'], ['SF_E2']) +
    '<bpmn2:endEvent id="EndEvent_Error" name="Error End">' +
    props({'componentVersion': '1.1', 'cmdVariantUri': 'ctype::FlowstepVariant/cname::MessageEndEvent/version::1.1.0'}) +
    '<bpmn2:incoming>SF_E2</bpmn2:incoming><bpmn2:messageEventDefinition/></bpmn2:endEvent>' +
    seq('SF_E1', 'StartEvent_Error', 'CA_Error') + seq('SF_E2', 'CA_Error', 'EndEvent_Error') +
    '</bpmn2:subProcess>'
)

process = (
    '<bpmn2:process id="Process_1" name="Integration Process">' + props({
        'transactionTimeout': '30', 'componentVersion': '1.1',
        'cmdVariantUri': 'ctype::FlowElementVariant/cname::IntegrationProcess/version::1.1.3',
        'transactionalHandling': 'Not Required'}) +
    exception_subprocess +
    '<bpmn2:startEvent id="StartEvent_1" name="Start">' +
    props({'cmdVariantUri': 'ctype::FlowstepVariant/cname::MessageStartEvent'}) +
    '<bpmn2:outgoing>SF_1</bpmn2:outgoing><bpmn2:messageEventDefinition/></bpmn2:startEvent>' +
    content_modifier('CA_Config', 'Read configuration', ['SF_1'], ['SF_2'],
                     properties=[('logPayloads', '{{LOG_PAYLOADS}}')]) +
    script('CA_LogRequest', 'Log request in', 'PayloadLogger.groovy', ['SF_2'], ['SF_3'], 'logRequest') +
    script('CA_Prepare', 'Parse request', 'PrepareRequest.groovy', ['SF_3'], ['SF_4']) +
    '<bpmn2:exclusiveGateway default="SF_Coords" id="ExclusiveGateway_Geo" name="City given?">' +
    props({'componentVersion': '1.1', 'activityType': 'ExclusiveGateway',
           'cmdVariantUri': 'ctype::FlowstepVariant/cname::ExclusiveGateway/version::1.1.2', 'throwException': 'false'}) +
    '<bpmn2:incoming>SF_4</bpmn2:incoming><bpmn2:outgoing>SF_City</bpmn2:outgoing>'
    '<bpmn2:outgoing>SF_Coords</bpmn2:outgoing></bpmn2:exclusiveGateway>' +
    request_reply('ST_Geocode', 'Geocode city', ['SF_City'], ['SF_5']) +
    script('CA_LogGeo', 'Log geocoding response', 'PayloadLogger.groovy', ['SF_5'], ['SF_6'], 'logDownstream') +
    script('CA_SetCoords', 'Set coordinates', 'SetCoordinates.groovy', ['SF_6'], ['SF_7']) +
    script('CA_BuildQuery', 'Build forecast query', 'BuildForecastQuery.groovy', ['SF_Coords', 'SF_7'], ['SF_8']) +
    request_reply('ST_Forecast', 'Get current weather', ['SF_8'], ['SF_9']) +
    script('CA_LogForecast', 'Log forecast response', 'PayloadLogger.groovy', ['SF_9'], ['SF_10'], 'logDownstream') +
    json_to_xml('CA_JsonToXml', 'Forecast JSON to XML', ['SF_10'], ['SF_11']) +
    xslt('CA_Mapping', 'Map to WeatherReport', 'WeatherReport', ['SF_11'], ['SF_12']) +
    xml_to_json('CA_XmlToJson', 'WeatherReport XML to JSON', ['SF_12'], ['SF_13']) +
    content_modifier('CA_Response', 'Set response headers', ['SF_13'], ['SF_14'],
                     headers=[('Content-Type', 'application/json'), ('CamelHttpResponseCode', '200')]) +
    script('CA_LogOutput', 'Log final output', 'PayloadLogger.groovy', ['SF_14'], ['SF_15'], 'logOutput') +
    '<bpmn2:endEvent id="EndEvent_1" name="End">' +
    props({'componentVersion': '1.1', 'cmdVariantUri': 'ctype::FlowstepVariant/cname::MessageEndEvent/version::1.1.0'}) +
    '<bpmn2:incoming>SF_15</bpmn2:incoming><bpmn2:messageEventDefinition/></bpmn2:endEvent>' +
    ''.join(seq(f, s, t) for f, s, t in chain if f not in ('SF_City', 'SF_Coords', 'SF_E1', 'SF_E2')) +
    seq('SF_City', 'ExclusiveGateway_Geo', 'ST_Geocode', name='City', condition="${property.needGeocode} = 'true'") +
    seq('SF_Coords', 'ExclusiveGateway_Geo', 'CA_BuildQuery', name='Coordinates', xml_route=True) +
    '</bpmn2:process>'
)

di = ['<bpmndi:BPMNDiagram id="BPMNDiagram_1" name="Default Collaboration Diagram"><bpmndi:BPMNPlane bpmnElement="Collaboration_1" id="BPMNPlane_1">']
for e, (x, y, w, h) in shapes.items():
    di.append(f'<bpmndi:BPMNShape bpmnElement="{e}" id="BPMNShape_{e}"><dc:Bounds height="{h}.0" width="{w}.0" x="{x}.0" y="{y}.0"/></bpmndi:BPMNShape>')
for f, s, t in edges:
    (x1, y1), (x2, y2) = center(s), center(t)
    di.append(f'<bpmndi:BPMNEdge bpmnElement="{f}" id="BPMNEdge_{f}" sourceElement="BPMNShape_{s}" targetElement="BPMNShape_{t}">'
              f'<di:waypoint x="{x1}" xsi:type="dc:Point" y="{y1}"/><di:waypoint x="{x2}" xsi:type="dc:Point" y="{y2}"/></bpmndi:BPMNEdge>')
di.append('</bpmndi:BPMNPlane></bpmndi:BPMNDiagram>')

iflw = ('<?xml version="1.0" encoding="UTF-8"?><bpmn2:definitions xmlns:bpmn2="http://www.omg.org/spec/BPMN/20100524/MODEL" '
        'xmlns:bpmndi="http://www.omg.org/spec/BPMN/20100524/DI" xmlns:dc="http://www.omg.org/spec/DD/20100524/DC" '
        'xmlns:di="http://www.omg.org/spec/DD/20100524/DI" xmlns:ifl="http:///com.sap.ifl.model/Ifl.xsd" '
        'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" id="Definitions_1">'
        + collaboration + process + ''.join(di) + '</bpmn2:definitions>')


def esc_prop(v):
    return v.replace('\\', '\\\\').replace(':', '\\:').replace('=', '\\=')


def parameters_prop():
    return '#Store parameters\n' + ''.join(f'{k}={esc_prop(v[0])}\n' for k, v in PARAMS.items())


def parameters_propdef():
    ps = ''.join(f'<parameter><key/><name>{k}</name><type>xsd:string</type><isRequired>false</isRequired>'
                 f'<constraint/><description>{d}</description><additionalMetadata/></parameter>' for k, (v, d) in PARAMS.items())
    return f'<?xml version="1.0" encoding="UTF-8"?><parameters>{ps}</parameters>'


def build(out_dir=ROOT):
    """Writes the abapGit-style source tree (for git / CI/CD) and the upload zip."""
    res = os.path.join(out_dir, 'src/main/resources')
    files = {
        'META-INF/MANIFEST.MF': manifest(),
        'metainfo.prop': 'description=Weather Data v2 - refactored copy of Weather_Data: externalized URLs, XSLT mapping, exception subprocess, MPL payload logging.\n',
        'src/main/resources/parameters.prop': parameters_prop(),
        'src/main/resources/parameters.propdef': parameters_propdef(),
        f'src/main/resources/scenarioflows/integrationflow/{IFLOW_ID}.iflw': iflw,
    }
    for rel, content in files.items():
        p = os.path.join(out_dir, rel); os.makedirs(os.path.dirname(p), exist_ok=True)
        with open(p, 'w', newline='') as fh: fh.write(content)
    zip_path = os.path.join(ROOT, f'{IFLOW_ID}.zip')
    with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as z:
        for rel in files: z.write(os.path.join(out_dir, rel), rel)
        for sub in ('script', 'mapping'):
            for f in sorted(os.listdir(os.path.join(res, sub))):
                z.write(os.path.join(res, sub, f), f'src/main/resources/{sub}/{f}')
    return zip_path


if __name__ == '__main__':
    print(build())
