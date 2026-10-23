<?xml version="1.0" encoding="UTF-8"?>
<!--
  WeatherReport.xsl - maps the Open-Meteo forecast response (after JSON-to-XML conversion,
  root element "root") to the clean WeatherReport structure returned by Weather_Data_v2.
  Exchange properties set earlier in the flow arrive as XSLT parameters.
-->
<xsl:stylesheet version="2.0" xmlns:xsl="http://www.w3.org/1999/XSL/Transform">
  <xsl:output method="xml" encoding="UTF-8" indent="no"/>

  <xsl:param name="locationName"/>
  <xsl:param name="locationRegion"/>
  <xsl:param name="locationCountry"/>
  <xsl:param name="units"/>

  <!-- WMO weather interpretation codes used by Open-Meteo -->
  <xsl:variable name="wmo">
    <c k="0">Clear sky</c><c k="1">Mainly clear</c><c k="2">Partly cloudy</c><c k="3">Overcast</c>
    <c k="45">Fog</c><c k="48">Depositing rime fog</c>
    <c k="51">Light drizzle</c><c k="53">Moderate drizzle</c><c k="55">Dense drizzle</c>
    <c k="56">Light freezing drizzle</c><c k="57">Dense freezing drizzle</c>
    <c k="61">Slight rain</c><c k="63">Moderate rain</c><c k="65">Heavy rain</c>
    <c k="66">Light freezing rain</c><c k="67">Heavy freezing rain</c>
    <c k="71">Slight snow</c><c k="73">Moderate snow</c><c k="75">Heavy snow</c><c k="77">Snow grains</c>
    <c k="80">Slight rain showers</c><c k="81">Moderate rain showers</c><c k="82">Violent rain showers</c>
    <c k="85">Slight snow showers</c><c k="86">Heavy snow showers</c>
    <c k="95">Thunderstorm</c><c k="96">Thunderstorm with slight hail</c><c k="99">Thunderstorm with heavy hail</c>
  </xsl:variable>

  <xsl:template match="/">
    <xsl:variable name="r" select="/*"/>
    <xsl:variable name="code" select="normalize-space($r/current/weather_code)"/>
    <xsl:variable name="desc" select="$wmo/c[@k = $code]"/>
    <WeatherReport>
      <location>
        <name><xsl:value-of select="$locationName"/></name>
        <region><xsl:value-of select="$locationRegion"/></region>
        <country><xsl:value-of select="$locationCountry"/></country>
        <latitude><xsl:value-of select="$r/latitude"/></latitude>
        <longitude><xsl:value-of select="$r/longitude"/></longitude>
        <timezone><xsl:value-of select="$r/timezone"/></timezone>
        <elevation><xsl:value-of select="$r/elevation"/></elevation>
      </location>
      <current>
        <observedAt><xsl:value-of select="$r/current/time"/></observedAt>
        <temperature><xsl:value-of select="$r/current/temperature_2m"/></temperature>
        <feelsLike><xsl:value-of select="$r/current/apparent_temperature"/></feelsLike>
        <humidity><xsl:value-of select="$r/current/relative_humidity_2m"/></humidity>
        <windSpeed><xsl:value-of select="$r/current/wind_speed_10m"/></windSpeed>
        <weatherCode><xsl:value-of select="$code"/></weatherCode>
        <conditions>
          <xsl:choose>
            <xsl:when test="$desc"><xsl:value-of select="$desc"/></xsl:when>
            <xsl:when test="$code = ''">Unknown</xsl:when>
            <xsl:otherwise><xsl:value-of select="concat('Weather code ', $code)"/></xsl:otherwise>
          </xsl:choose>
        </conditions>
      </current>
      <units>
        <system><xsl:value-of select="if ($units != '') then $units else 'metric'"/></system>
        <temperature><xsl:value-of select="$r/current_units/temperature_2m"/></temperature>
        <windSpeed><xsl:value-of select="$r/current_units/wind_speed_10m"/></windSpeed>
        <humidity><xsl:value-of select="$r/current_units/relative_humidity_2m"/></humidity>
      </units>
      <mappedBy>XSLT WeatherReport.xsl (Weather_Data_v2)</mappedBy>
      <source>Open-Meteo (open-meteo.com)</source>
    </WeatherReport>
  </xsl:template>
</xsl:stylesheet>
