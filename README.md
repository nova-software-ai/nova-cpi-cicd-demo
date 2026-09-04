# NovaLocIntelV2 — SAP Integration Suite artifact under source control

Cloud Integration iFlow managed as code and promoted by SAP Continuous
Integration and Delivery (pipeline type `cpi`, "SAP Integration Suite Artifacts").

    src/main/resources/scenarioflows/integrationflow/   BPMN process definition
    src/main/resources/script/                          Groovy steps
    src/main/resources/parameters.propdef|.prop         externalized configuration
    META-INF/MANIFEST.MF                                bundle metadata
    integrationTest/messageBody                         payload for the Integration Test stage

Pipeline stages: Upload (Git -> tenant) -> Deploy -> Integration Test.
Design-time auth: `nova-cpi-api-key` (Process Integration Runtime, plan `api`).
Runtime auth:     `nova-cpi-runtime-key` (plan `integration-flow`).
