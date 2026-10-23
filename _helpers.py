"""Generates the Weather_Data iFlow (BPMN .iflw + bundle files) and zips it for upload to SAP Cloud Integration."""
import os, zipfile, textwrap

ROOT = os.path.dirname(os.path.abspath(__file__))
IFLOW_ID = 'Weather_Data_v2'
IFLOW_NAME = 'Weather Data v2'


def props(d):
    out = []
    for k, v in d.items():
        v = '' if v is None else str(v)
        v = v.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
        out.append(f'<ifl:property><key>{k}</key>' + (f'<value>{v}</value>' if v else '<value/>') + '</ifl:property>')
    return '<bpmn2:extensionElements>' + ''.join(out) + '</bpmn2:extensionElements>'


def http_receiver(flow_id, name, source, target, url, query):
    return f'<bpmn2:messageFlow id="{flow_id}" name="HTTP" sourceRef="{source}" targetRef="{target}">' + props({
        'Description': f'Call {name}', 'methodSourceExpression': '', 'ComponentNS': 'sap', 'privateKeyAlias': '',
        'httpMethod': 'GET', 'Name': 'HTTP', 'TransportProtocolVersion': '1.7.2', 'ComponentSWCVName': 'external',
        'proxyPort': '', 'httpAddressQuery': query, 'httpRequestTimeout': '60000', 'MessageProtocol': 'None',
        'ComponentSWCVId': '1.7.2', 'direction': 'Receiver', 'ComponentType': 'HTTP', 'httpShouldSendBody': 'false',
        'proxyType': 'default', 'componentVersion': '1.7', 'proxyHost': '', 'system': name,
        'authenticationMethod': 'None', 'locationID': '', 'TransportProtocol': 'HTTP',
        'cmdVariantUri': 'ctype::AdapterVariant/cname::sap:HTTP/tp::HTTP/mp::None/direction::Receiver/version::1.7.2',
        'credentialName': '', 'MessageProtocolVersion': '1.7.2', 'httpAddressWithoutQuery': url,
    }) + '</bpmn2:messageFlow>'


def script(step_id, name, file, incoming, outgoing):
    return f'<bpmn2:callActivity id="{step_id}" name="{name}">' + props({
        'scriptFunction': '', 'componentVersion': '1.0', 'activityType': 'Script',
        'cmdVariantUri': 'ctype::FlowstepVariant/cname::GroovyScript/version::1.0.1',
        'subActivityType': 'GroovyScript', 'script': file,
    }) + ''.join(f'<bpmn2:incoming>{i}</bpmn2:incoming>' for i in incoming) + \
        ''.join(f'<bpmn2:outgoing>{o}</bpmn2:outgoing>' for o in outgoing) + '</bpmn2:callActivity>'


def request_reply(step_id, name, incoming, outgoing):
    return f'<bpmn2:serviceTask id="{step_id}" name="{name}">' + props({
        'componentVersion': '1.0', 'activityType': 'ExternalCall',
        'cmdVariantUri': 'ctype::FlowstepVariant/cname::ExternalCall/version::1.0.4',
    }) + ''.join(f'<bpmn2:incoming>{i}</bpmn2:incoming>' for i in incoming) + \
        ''.join(f'<bpmn2:outgoing>{o}</bpmn2:outgoing>' for o in outgoing) + '</bpmn2:serviceTask>'


def seq(flow_id, src, tgt, name=None, condition=None, xml_route=False):
    attrs = f'id="{flow_id}"' + (f' name="{name}"' if name else '') + f' sourceRef="{src}" targetRef="{tgt}"'
    if condition is None and not xml_route:
        return f'<bpmn2:sequenceFlow {attrs}/>'
    body = props({'expressionType': 'XML' if xml_route else 'NonXML', 'componentVersion': '1.0',
                  'cmdVariantUri': 'ctype::FlowstepVariant/cname::GatewayRoute/version::1.0.0'})
    if condition:
        body += f'<bpmn2:conditionExpression id="FormalExpression_{flow_id}" xsi:type="bpmn2:tFormalExpression">{condition}</bpmn2:conditionExpression>'
    return f'<bpmn2:sequenceFlow {attrs}>{body}</bpmn2:sequenceFlow>'



def manifest():
    imports = ('com.sap.esb.application.services.cxf.interceptor,com.sap.esb.security,com.sap.it.op.agent.api,'
               'com.sap.it.op.agent.collector.camel,com.sap.it.op.agent.collector.cxf,com.sap.it.op.agent.mpl,javax.jms,'
               'javax.jws,javax.wsdl,javax.xml.bind.annotation,javax.xml.namespace,javax.xml.ws,org.apache.camel;version="2.8",'
               'org.apache.camel.builder;version="2.8",org.apache.camel.builder.xml;version="2.8",org.apache.camel.component.cxf,'
               'org.apache.camel.model;version="2.8",org.apache.camel.processor;version="2.8",'
               'org.apache.camel.processor.aggregate;version="2.8",org.apache.camel.spring.spi;version="2.8",'
               'org.apache.commons.logging,org.apache.cxf.binding,org.apache.cxf.binding.soap,org.apache.cxf.binding.soap.spring,'
               'org.apache.cxf.bus,org.apache.cxf.bus.resource,org.apache.cxf.bus.spring,org.apache.cxf.buslifecycle,'
               'org.apache.cxf.catalog,org.apache.cxf.configuration.jsse;version="2.5",org.apache.cxf.configuration.spring,'
               'org.apache.cxf.endpoint,org.apache.cxf.headers,org.apache.cxf.interceptor,'
               'org.apache.cxf.management.counters;version="2.5",org.apache.cxf.message,org.apache.cxf.phase,'
               'org.apache.cxf.resource,org.apache.cxf.service.factory,org.apache.cxf.service.model,org.apache.cxf.transport,'
               'org.apache.cxf.transport.common.gzip,org.apache.cxf.transport.http,org.apache.cxf.transport.http.policy,'
               'org.apache.cxf.workqueue,org.apache.cxf.ws.rm.persistence,org.apache.cxf.wsdl11,org.osgi.framework;version="1.6.0",'
               'org.slf4j;version="1.6",org.springframework.beans.factory.config;version="3.0",com.sap.esb.camel.security.cms,'
               'org.apache.camel.spi,com.sap.esb.webservice.audit.log,com.sap.esb.camel.endpoint.configurator.api,'
               'com.sap.esb.camel.jdbc.idempotency.reorg,javax.sql,org.apache.camel.processor.idempotent.jdbc,'
               'org.osgi.service.blueprint;version="[1.0.0,2.0.0)"')
    services = ('com.sap.esb.webservice.audit.log.AuditLogger,com.sap.esb.security.KeyManagerFactory;multiple:=false,'
                'com.sap.esb.security.TrustManagerFactory;multiple:=false,javax.sql.DataSource;multiple:=false;'
                'filter="(dataSourceName=default)",org.apache.cxf.ws.rm.persistence.RMStore;multiple:=false,'
                'com.sap.esb.camel.security.cms.SignatureSplitter;multiple:=false')
    lines = [('Manifest-Version', '1.0'), ('SAP-RuntimeProfile', 'iflmap'),
             ('Bundle-SymbolicName', f'{IFLOW_ID}; singleton:=true'), ('Bundle-Name', IFLOW_NAME),
             ('Bundle-Version', '1.0.0'), ('Bundle-ManifestVersion', '2'), ('SAP-NodeType', 'IFLMAP'),
             ('Import-Package', imports), ('SAP-BundleType', 'IntegrationFlow'), ('Import-Service', services),
             ('Origin-Bundle-Name', IFLOW_NAME), ('Origin-Bundle-SymbolicName', IFLOW_ID)]
    out = []
    for k, v in lines:  # wrap at 72 bytes per JAR manifest spec
        full = f'{k}: {v}'
        out.append(full[:72])
        rest = full[72:]
        while rest:
            out.append(' ' + rest[:71]); rest = rest[71:]
    return '\r\n'.join(out) + '\r\n\r\n'


