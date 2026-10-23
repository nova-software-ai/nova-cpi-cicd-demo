# Weather_Data_v2 — SAP Cloud Integration iFlow under source control

Copy of `Weather_Data` (package `WeatherData`) refactored for the ExxonMobil capability demo.
See CHANGES.md for before/after. Promoted by SAP Continuous Integration and Delivery,
pipeline "SAP Integration Suite Artifacts" (Upload -> Deploy -> Integration Test), configured in `.pipeline/config.yml`.

    META-INF/MANIFEST.MF, metainfo.prop                  bundle metadata
    src/main/resources/scenarioflows/integrationflow/    BPMN model (Weather_Data_v2.iflw)
    src/main/resources/script/                           Groovy steps
    src/main/resources/mapping/WeatherReport.xsl         XSLT mapping
    src/main/resources/parameters.prop|.propdef          externalized parameters
    integrationTest/messageBody                          payload for the Integration Test stage
    build_iflow_v2.py                                    generator for the .iflw and the upload zip
