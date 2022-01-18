package mmc_json_new;

import java.io.BufferedReader;
import java.io.File;
import java.io.FileInputStream;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.net.URL;
import java.security.KeyStore;
import java.security.SecureRandom;
import java.security.cert.CertificateException;
import java.security.cert.X509Certificate;
import java.util.Base64;
import java.util.stream.Collectors;

import javax.net.ssl.HostnameVerifier;
import javax.net.ssl.HttpsURLConnection;
import javax.net.ssl.KeyManagerFactory;
import javax.net.ssl.SSLContext;
import javax.net.ssl.SSLSocketFactory;
import javax.net.ssl.TrustManager;
import javax.net.ssl.TrustManagerFactory;
import javax.net.ssl.X509TrustManager;
import javax.net.ssl.KeyManager;

import org.apache.http.HttpEntity;
import org.apache.http.client.methods.CloseableHttpResponse;
import org.apache.http.client.methods.HttpGet;
import org.apache.http.client.methods.HttpPut;
import org.apache.http.client.methods.HttpUriRequest;
import org.apache.http.config.Registry;
import org.apache.http.config.RegistryBuilder;
import org.apache.http.conn.HttpClientConnectionManager;
import org.apache.http.conn.socket.ConnectionSocketFactory;
import org.apache.http.conn.socket.PlainConnectionSocketFactory;
import org.apache.http.conn.ssl.NoopHostnameVerifier;
import org.apache.http.conn.ssl.SSLConnectionSocketFactory;
import org.apache.http.impl.client.CloseableHttpClient;
import org.apache.http.impl.client.HttpClientBuilder;
import org.apache.http.impl.client.HttpClients;
import org.apache.http.impl.conn.BasicHttpClientConnectionManager;
import org.apache.http.impl.conn.PoolingHttpClientConnectionManager;
import org.apache.http.util.EntityUtils;

import java.io.File;  
import java.io.FileOutputStream;
import java.io.InputStreamReader;  
import java.io.BufferedReader;  
import java.io.BufferedWriter;  
import java.io.FileInputStream;  
import java.io.FileWriter; 
import java.util.HashMap;
import java.util.Map;
import java.util.Set;

import com.alibaba.fastjson.JSON;
import com.alibaba.fastjson.JSONArray;
import com.alibaba.fastjson.JSONObject;

import org.apache.http.entity.StringEntity;


public class mmc_test {
	// MMC INT env
	public static String clientTrustCertificateFile = "D:/TECHNICALACCOUNTCHINACCM_NONPROD.pfx";
	public static String clientTrustCertificatePwd = "Px57ZpMb2n6K9Xmg8LFs";
	public static String baseURL = "https://api-cn-int-cert.cn.corpinter.net/int/";
	public static String assignmentAPIPath = "connectedvehicle/servicemgmt/assignmentsapi/v2/";
	public static String serviceAPIPath = "connectedvehicle/servicemgmt/servicesapi/v2/";
	public static String techUserAndPwd = "MBC_CCM_00000" + ":" + "XhMm8T73kz";
    public static String basicAuthEncoding = new String(Base64.getEncoder().encode(techUserAndPwd.getBytes()));
    public static String activeVinFile = "D:/Active_VIN";
    public static String logFile = "D:/mmc_log";
	public static String cacertsFile = "D:/cacerts";
	public static String cacertsPwd = "changeit";
	public static String appName = "CoCaMa_Test";
	public static String trackingId = "beda15a0-47eb-4242-b919-7ec5f0f89630";
	public static String ccmPartnerId = "MBC.CNCCM";


	// MMC PROD env
	/*
	public static String clientTrustCertificateFile = "D:/TECHNICALACCOUNTCHINACCM_PROD.pfx";
	public static String clientTrustCertificatePwd = "e2C0Ppk9Y4Bgl5F8Awh7";
	public static String baseURL = "https://api-cn-cert.cn.corpinter.net/prod/";
	public static String assignmentAPIPath = "connectedvehicle/servicemgmt/assignmentsapi/v2/";
	public static String serviceAPIPath = "connectedvehicle/servicemgmt/servicesapi/v2/";
	public static String techUserAndPwd = "MBC_CCM_00000" + ":" + "En4Cr8XBMD";
    public static String basicAuthEncoding = new String(Base64.getEncoder().encode(techUserAndPwd.getBytes()));
    public static String activeVinFile = "D:/Active_VIN";
    public static String logFile = "D:/mmc_log";
	public static String cacertsFile = "D:/cacerts";
	public static String cacertsPwd = "changeit";
	public static String appName = "CoCaMa_Test";
	public static String trackingId = "42c3e7d2-4982-45bf-be10-8fecf376089a";
	public static String ccmPartnerId = "MBC.CNCCM"; 
	*/
	
	
	public static void testMMCBeforePush(String vin, SSLContext sslContext, KeyManager[] kms, TrustManager[] tms) throws Exception
    {
	    HostnameVerifier hostnameVerifier = NoopHostnameVerifier.INSTANCE;   
	    HttpsURLConnection.setDefaultSSLSocketFactory(sslContext.getSocketFactory());
	    HttpsURLConnection.setDefaultHostnameVerifier(hostnameVerifier);

	    // 1st API: getParterIdsForVehicle
	    URL url = new URL(baseURL + assignmentAPIPath + "vehicles/" + vin + "/partnerids");
	    HttpsURLConnection con =  (HttpsURLConnection)url.openConnection();
	    if (con != null)
	    {
		    con.setRequestMethod("GET");
			con.setRequestProperty("finOrVin", vin);
			con.setRequestProperty("X-ApplicationName", appName);
			con.setRequestProperty("X-TrackingId", trackingId);
			con.setRequestProperty("Authorization", "Basic " + basicAuthEncoding);
			System.out.println(basicAuthEncoding);
			con.setRequestProperty("Connection", "keep-alive");
			con.setRequestProperty("Cache-Control", "no-cache");

		    // con.setSSLSocketFactory(sslContext.getSocketFactory()); 
		    con.connect();

		    int responseCode = con.getResponseCode();
		    if (responseCode == 200)
		    {
			    InputStream response = con.getInputStream();
			    if (response != null)
			    {
				    String result = new BufferedReader(new InputStreamReader(response)).lines().collect(Collectors.joining("\n"));
				    System.out.println("Vin: " + vin + ", Response Code: " + con.getResponseCode() + ", \nMessage: \n" + result);
				    response.close();
			    }	
		    }

		    con.disconnect();
	    	con = null;
	    }
	    
	    
		// -----------------------------------------------------------------------------------------
		// -----------------------------------------------------------------------------------------
		
		
	    /*
	    url = new URL(baseURL + serviceAPIPath + "vehicles/" + vin + "/partners/" + ccmPartnerId + "/services");
	    con =  (HttpsURLConnection)url.openConnection();
	    if (con != null)
	    {
		    con.setRequestMethod("PUT");
		    JSONObject serviceObj = new JSONObject();
		    serviceObj.put("serviceId", 2001);
		    serviceObj.put("desiredServiceStatus", "ACTIVE");
		    
		    JSONObject serviceFinalObj = new JSONObject();
		    serviceFinalObj.put("services", serviceObj);
		    
			con.setRequestProperty("finOrVin", vin);
			con.setRequestProperty("partnerId", ccmPartnerId);
		    con.setRequestProperty("requestBody", serviceFinalObj.toString());
			con.setRequestProperty("X-ApplicationName", appName);
			con.setRequestProperty("X-TrackingId", trackingId);
			con.setRequestProperty("Authorization", "Basic " + basicAuthEncoding);
			con.setRequestProperty("Connection", "keep-alive");
			con.setRequestProperty("Cache-Control", "no-cache");

		    // con.setSSLSocketFactory(sslContext.getSocketFactory()); 
		    con.connect();

		    int responseCode = con.getResponseCode();
		    if (responseCode == 202)
		    {
			    InputStream response = con.getInputStream();
			    if (response != null)
			    {
				    String result = new BufferedReader(new InputStreamReader(response)).lines().collect(Collectors.joining("\n"));
				    System.out.println("Vin: " + vin + ", Response Code: " + con.getResponseCode() + ", \nMessage: \n" + result);
				    response.close();
			    }	
		    }
		    else 
		    {
		    	System.out.println("Vin: " + vin + ", Response Code: " + responseCode + ", \nMessage: \n" + con.getResponseMessage());
		    }

		    con.disconnect();
	    	con = null;
	    }
	    */
    }
    
	public static void main( String[] args ) throws Exception
	{
        // create hashMap of Vin-PartnerId
        Map<String, String> vinMap = new HashMap<String, String>();
        File vinFile = new File(activeVinFile);
        InputStreamReader reader = new InputStreamReader(new FileInputStream(vinFile));
        BufferedReader br = new BufferedReader(reader);
        String line = "";
        line = br.readLine();
        while (line != null)
        {
        	if (line.length() == 17)
        	{
        		vinMap.put(line, "");
        	}
        	
        	line = br.readLine();
        }
        
        br.close();
        reader.close();
        
		// step 1: copy TECHNICALACCOUNTCHINACCM_NONPROD.cer under %JAVA_HOME%/jre/lib/security
		// step 2: run command line as admin, under %JAVE_HOME%/jre/lib/security, execute:
		// keytool -import -alias mmc_nonprod -keystore cacerts -file TECHNICALACCOUNTCHINACCM_NONPROD.cer -trustcacerts
		// step 3: Copy cacerts from C:/Program Files/Java/jre1.8.0_202/lib/security to D:
		KeyStore clientStore = KeyStore.getInstance("PKCS12");
		clientStore.load(new FileInputStream(new File(clientTrustCertificateFile)), clientTrustCertificatePwd.toCharArray());
	    KeyManagerFactory kmf = KeyManagerFactory.getInstance(KeyManagerFactory.getDefaultAlgorithm());
	    kmf.init(clientStore, clientTrustCertificatePwd.toCharArray());
	    KeyManager[] kms = kmf.getKeyManagers();
		
	    KeyStore trustStore = KeyStore.getInstance("JKS");
	    trustStore.load(new FileInputStream(cacertsFile), cacertsPwd.toCharArray());

	    TrustManagerFactory tmf = TrustManagerFactory.getInstance(TrustManagerFactory.getDefaultAlgorithm());
	    tmf.init(trustStore);
	    TrustManager[] tms = tmf.getTrustManagers();

	    final SSLContext sslContext = SSLContext.getInstance("TLS");
	    sslContext.init(kms,tms,new SecureRandom());
	    SSLContext.setDefault(sslContext);
	    
	    // test VIns that can be found provided by MMC
	    // testMMCBeforePush("WDDSJ4HB2JN603741", sslContext, kms, tms);
	    // testMMCBeforePush("LE43X8HB9KL000331", sslContext, kms, tms);
	    // testMMCBeforePush("LE43X8HB9KL023074", sslContext, kms, tms);
	    
	    // Method 1: use HttpsURLConnection
	    HostnameVerifier hostnameVerifier = NoopHostnameVerifier.INSTANCE;   
	    HttpsURLConnection.setDefaultSSLSocketFactory(sslContext.getSocketFactory());
	    HttpsURLConnection.setDefaultHostnameVerifier(hostnameVerifier);

        File logs = new File(logFile);
        if (!logs.exists())
        {
        	logs.createNewFile();
        }
        
        FileWriter fileWriter = new FileWriter(logs.getName(), true);
        BufferedWriter bufferWriter = new BufferedWriter(fileWriter); 

	    Set<Map.Entry<String, String>> set = vinMap.entrySet();
	    for (Map.Entry<String, String> me : set) 
	    {
	    	String vin = me.getKey();

	    	URL url = new URL(baseURL + assignmentAPIPath + "vehicles/" + vin + "/partnerids");
		    HttpsURLConnection con =  (HttpsURLConnection)url.openConnection();
		    if (con != null)
		    {
			    con.setRequestMethod("GET");
				con.setRequestProperty("finOrVin", vin);
				con.setRequestProperty("X-ApplicationName", "CoCaMa_Test");
				con.setRequestProperty("X-TrackingId", "beda15a0-47eb-4242-b919-7ec5f0f89630");
				con.setRequestProperty("Authorization", "Basic " + basicAuthEncoding);
				con.setRequestProperty("Connection", "keep-alive");
				con.setRequestProperty("Cache-Control", "no-cache");

			    // con.setSSLSocketFactory(sslContext.getSocketFactory()); 
			    con.connect();

			    int responseCode = con.getResponseCode();
			    if (responseCode == 200)
			    {
				    InputStream response = con.getInputStream();
				    if (response != null)
				    {
					    String result = new BufferedReader(new InputStreamReader(response)).lines().collect(Collectors.joining("\n"));
					    System.out.println("Vin: " + vin + ", Response Code: " + con.getResponseCode() + ", Message: " + result);
					    // bufferWriter.write("Vin: " + vin + ", Response Code: " + con.getResponseCode() + ", Message: " + result + "\n");
					    response.close();
				    }	
			    }

			    con.disconnect();
		    	con = null;
		    }
	    }
	    
	    bufferWriter.close();

    
	    // Method 1: use HttpsURLConnection
	    /*
	    HostnameVerifier hostnameVerifier = NoopHostnameVerifier.INSTANCE;   
	    HttpsURLConnection.setDefaultSSLSocketFactory(sslContext.getSocketFactory());
	    HttpsURLConnection.setDefaultHostnameVerifier(hostnameVerifier);

	    URL url = new URL(baseURL + assignmentAPIPath + "vehicles/WDCYC7CF9JX284752/partnerids");
	    HttpsURLConnection con =  (HttpsURLConnection)url.openConnection();
	    if (con != null)
	    {
		    con.setRequestMethod("GET");
			con.setRequestProperty("finOrVin", "WDCYC7CF9JX284752");
			con.setRequestProperty("X-ApplicationName", "CoCaMa_Test");
			con.setRequestProperty("X-TrackingId", "beda15a0-47eb-4242-b919-7ec5f0f89630");
			con.setRequestProperty("Authorization", "Basic " + basicAuthEncoding);
			con.setRequestProperty("Connection", "keep-alive");
			con.setRequestProperty("Cache-Control", "no-cache");

		    // con.setSSLSocketFactory(sslContext.getSocketFactory()); 
		    con.connect();

		    InputStream response = con.getInputStream();
		    if (response != null)
		    {
			    String result = new BufferedReader(new InputStreamReader(response)).lines().collect(Collectors.joining("\n"));
			    System.out.println("Response Code_1: " + con.getResponseCode() + ", \nResponse of API_1 is: \n" + result);
			    response.close();
		    }	

	    	con.disconnect();
	    	con = null;
	    }
	    */
	    // End of method 1
	    
	    // Method 2: use HttpClient (version 4.5.8)
		/*
	    SSLContext sslCtx = SSLContext.getInstance("TLS");
	    sslCtx.init(kms, tms, new SecureRandom());
		SSLConnectionSocketFactory sslConnectionFactory = new SSLConnectionSocketFactory(sslCtx);
		// Start of Way 1:
		// HttpClientBuilder hcb = HttpClientBuilder.create();
		// hcb.setSSLSocketFactory(sslConnectionFactory);
		// CloseableHttpClient closeableHttpClient = hcb.build();
		// End of Way 1
		
		// Start of Way 2:
		Registry<ConnectionSocketFactory> registry = RegistryBuilder.<ConnectionSocketFactory>create().register("https", sslConnectionFactory).register("http", new PlainConnectionSocketFactory()).build();
		// HttpClientConnectionManager cm = new BasicHttpClientConnectionManager(registry);
		PoolingHttpClientConnectionManager cm = new PoolingHttpClientConnectionManager(registry);
		HttpClientBuilder hcb = HttpClientBuilder.create();
		hcb.setConnectionManager(cm);
		CloseableHttpClient closeableHttpClient = hcb.build();
		// End of Way 2

		// Start of Way 3:
		// CloseableHttpClient closeableHttpClient = HttpClients.custom().setSSLSocketFactory(sslConnectionFactory).build();
		// End of Way 3
		
		HttpUriRequest httpGet = new
				HttpGet(baseURL + serviceAPIPath + "vehicles/WDCYC7CF9JX284752/partners/" + ccmPartnerId + "/services");
		httpGet.addHeader( "finOrVin", "WDCYC7CF9JX284752" );
		httpGet.addHeader( "partnerId", ccmPartnerId );
		httpGet.addHeader( "X-ApplicationName", "CoCaMa_Test" );
		httpGet.addHeader( "X-TrackingId",
				"beda15a0-47eb-4242-b919-7ec5f0f89630" );
		httpGet.addHeader("Authorization", "Basic " + basicAuthEncoding);
		httpGet.addHeader("Connection", "keep-alive");
		httpGet.addHeader("Cache-Control", "no-cache");
		
		CloseableHttpResponse response = closeableHttpClient
				.execute( httpGet );
		HttpEntity result = response.getEntity();
		if ( result != null )
		{
			String entityStr = EntityUtils.toString( result, "utf-8" );
			System.out.println( "\nResponse Code_2: " + response.getStatusLine() + ", \nResponse of API_2 is: \n" + entityStr );
		}
		
		closeableHttpClient.close();
		*/
	    // End of method 2
	}
}
