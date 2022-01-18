package com.dfscn.mdw.oidc;

import java.io.IOException;
import java.net.MalformedURLException;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import org.apache.log4j.Logger;
import org.jose4j.jwk.JsonWebKey;
import org.jose4j.jwk.JsonWebKeySet;
import org.jose4j.jwk.VerificationJwkSelector;
import org.jose4j.jws.JsonWebSignature;
import org.jose4j.lang.JoseException;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import com.dfscn.mdw.entity.ResultJson;
import com.dfscn.mdw.util.OAuth2Helper;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;


@RestController
@SpringBootApplication
public class OidcApplication {
	@Value("${AUTHORIZATION_ENDPOINT}")
	private String authorizationEndpoint;

	@Value("${CLIENT_ID}")
	private String clientId;

	@Value("${REDIRECT_URI}")
	private String redirectUri;

	@Value("${TOKEN_ENDPOINT}")
	private String tokenEndpoint;

	@Value("${CLIENT_SECRET}")
	private String clientSecret;

	@Value("${INTROSPECTION_ENDPOINT}")
	private String introspectionEndpoint;

	@Value("${CLIENT_ID_INTRO}")
	private String clientIdIntro;

	@Value("${CLIENT_SECRET_INTRO}")
	private String clientSecretIntro;

	@Value("${USERINFO_ENDPOINT}")
	private String userInfoEndpoint;

	@Value("${REVOCATION_ENDPOINT}")
	private String revocationEndpoint;

	@Value("${REDIRECT_TO_CLIENT}")
	private String redirectToClient;

	@Value("${JWKS_ENDPOINT}")
	private String JWKSEndpoint;
	
	@Value("${ESB_API_URL}")
	private String ESBAPIURL;
	
	private static Logger log = Logger.getLogger(OidcApplication.class.getClass());


	public static void main(String[] args) {
		SpringApplication.run(OidcApplication.class, args);
	}

	// Sends a redirect if the user needs to login.
	@RequestMapping("/redirectIfLoginRequired")
	public void redirectIfLoginRequired(HttpServletRequest request, HttpServletResponse response) {
		log.info("redirectIfLoginRequired begin");
		if (isLoginRequired(request)) {
			// Redirect to authorization endpoint to begin the login process
			try {
				String redirectUrl = createRedirectUrl();
				response.sendRedirect(redirectUrl);
			} catch (IOException e) {
				log.error("redirectIfLoginRequired failure," + e.getMessage());
			}
		}
		log.info("redirectIfLoginRequired finished");
	}

	/**
	 * @return true:need to login, false:no need
	 */
	@RequestMapping("/isLoginRequired")
	private boolean isLoginRequired(HttpServletRequest request) {
		log.info(" isLoginRequired begin ");
		boolean flag = true;

		// get access_token and ID_Token
		String accessToken = request.getParameter("access_token");
		String id_token = request.getParameter("id_token");

		if (accessToken == null || accessToken.equals("") || id_token == null || id_token.equals("")) {
			log.info("isLoginRequired, access_token or id_token is null ");
			flag = true;	
		} else {			
			//access token introspection, if access token is valid, accessTokenIntorFlag=true;
			OAuth2Helper oauth2Helper = new OAuth2Helper(introspectionEndpoint);
			boolean accessTokenIntorFlag = oauth2Helper.accessTokenIntrospection(clientIdIntro, clientSecretIntro,
					accessToken);
			log.info("isLoginRequired, accessTokenIntorFlag:" + accessTokenIntorFlag);
			// ID_Token verify
			boolean idTokenVerifyFlag = idTokenVerify(id_token);
			log.info("isLoginRequired, idTokenVerifyFlag:" + idTokenVerifyFlag);
			if(accessTokenIntorFlag ||idTokenVerifyFlag){
				flag = false;
			}else{
				flag = true;
			}
		}
		log.info("isLoginRequired finished, flag:" + flag);
		return flag;
	}

	/**
	 * Creates the redirect URL from configuration values.
	 *
	 * @param request
	 *            the request object.
	 * @return the redirect URL to be used.
	 * @throws MalformedURLException
	 *             Thrown to indicate that a malformed URL has occurred.
	 */
	@RequestMapping("/createRedirectUrl")
	private String createRedirectUrl() throws MalformedURLException {
		log.info("createRedirectUrl begin");
		
		String state = "";
		String redirectUrl = String.format("%s?response_type=code&client_id=%s&scope=openid&redirect_uri=%s&state=%s",
				authorizationEndpoint, clientId, redirectUri, state);

		log.info("createRedirectUrl finished");
		return redirectUrl;
	}

	//redirect URL
	@RequestMapping("/login")
	private void login(HttpServletRequest request, HttpServletResponse response) {
		log.info("login begin");

		String authCode = request.getParameter("code").toString();
		String rawToken = "";
		String accessTokenStr = "";
		String idTokenStr = "";
		String redirectUrl = "";
		int expiresInTime = 0;
		
		OAuth2Helper oauth2Helper = new OAuth2Helper(tokenEndpoint);

		try {
			//get access_token and id_token
			rawToken = oauth2Helper.swapAuthenticationCode(clientId, clientSecret, redirectUri, authCode);
			log.info("login begin rawToken" + rawToken);

			// Parse the token
			ObjectMapper mapper = new ObjectMapper();
			JsonNode resultJson = mapper.readTree(rawToken);

			JsonNode accessToken = resultJson.get("access_token");
			JsonNode idToken = resultJson.get("id_token");
			JsonNode expiresIn = resultJson.get("expires_in");
//			JsonNode refreshToken = resultJson.get("refresh_token");

			if(accessToken != null && !accessToken.equals("")){
				accessTokenStr = accessToken.asText();
			}
			if(idToken != null && !idToken.equals("")){
				idTokenStr = idToken.asText();
			}
			if(expiresIn != null && !expiresIn.equals("")){
				expiresInTime = expiresIn.asInt();
			}
			log.info("login begin accessTokenStr->" + accessToken);
			log.info("login begin idTokenStr->" + idToken);
			
			//Insert access_token and id_token to DB
			OAuth2Helper oauth2Helper1 = new OAuth2Helper(ESBAPIURL);
			String channel = "mobile";
			String updateResult = oauth2Helper1.updateUserToken(accessTokenStr, idTokenStr, expiresInTime, channel);
			
			log.info("login begin updateUserToken method result->" + updateResult);
			
			redirectUrl = String.format("%s?access_token=%s&id_token=%s",
					redirectToClient, accessTokenStr, idTokenStr);
			if(accessTokenStr == null || accessTokenStr.equals("") || idTokenStr == null || idTokenStr.equals("")){
				redirectUrl = String.format("%s?errorCode=%s&errorMessage=%s",
						redirectToClient, "1", "Failed to get access_token and id_token.");
			}
			//Insert token to DB fail
			if(!"SUCCESS".equals(updateResult)){
				redirectUrl = String.format("%s?errorCode=%s&errorMessage=%s",
						redirectToClient, "1", "Failed to insert access_token and id_token to DB.");
			}
			
			log.info("login finished, redirectUrl:" + redirectUrl);
			response.sendRedirect(redirectUrl);

		} catch (IOException e) {
			log.error("login failure," + e.getMessage());
		}
	}

	/**
	 * 
	 * @param idToken
	 * @return
	 */
	@RequestMapping("/idTokenVerify")
	private boolean idTokenVerify(String idToken) {
		log.info("idTokenVerify begin ");
		
		OAuth2Helper oauth2Helper = new OAuth2Helper(JWKSEndpoint);
		String jsonWebKeySetJson = oauth2Helper.getJWKS();
		log.info("idTokenVerify jsonWebKeySetJson" + jsonWebKeySetJson);
		
		String compactSerialization = idToken;

		// Create a new JsonWebSignature object
		JsonWebSignature jws = new JsonWebSignature();

		// Set the compact serialization on the JWS
		try {
			jws.setCompactSerialization(compactSerialization);
			// Create a new JsonWebKeySet object with the JWK Set JSON
			JsonWebKeySet jsonWebKeySet = new JsonWebKeySet(jsonWebKeySetJson);

			VerificationJwkSelector jwkSelector = new VerificationJwkSelector();
			JsonWebKey jwk = jwkSelector.select(jws, jsonWebKeySet.getJsonWebKeys());

			// The verification key on the JWS is the public key from the JWK we pulled from the JWK Set.
			jws.setKey(jwk.getKey());

			// Check the signature
			jws.verifySignature();
			log.info("idTokenVerify finishedid, TokenVerify JWS Signature is valid");
		} catch (JoseException e) {
			log.error("idTokenVerify failure," + e.getMessage());
			return false;
		}
		return true;
	}

	/**
	 * 
	 * @param accessToken
	 * @return success: {"sub":"xxx"} error: 401 - Unauthorized
	 */
	@RequestMapping("/getUserInfo")
	private String getUserInfo(String accessToken) {
		log.info("getUserInfo begin ");

		OAuth2Helper oauth2Helper = new OAuth2Helper(userInfoEndpoint);
		String resultJson = oauth2Helper.getUserInfo(userInfoEndpoint, accessToken);
		
		log.info("getUserInfo finished");
		return resultJson;
	}

	/**
	 * revocation access_token
	 * @param  token
	 */
	@RequestMapping("/revocationAccessToken")
	private ResultJson revocationAccessToken(String token) {
		log.info("revocationAccessToken begin");
		
		OAuth2Helper oauth2Helper = new OAuth2Helper(revocationEndpoint);
		boolean flag = oauth2Helper.revocationAccessToken(clientId, clientSecret, token);
		ResultJson res = new ResultJson();
		if(flag){
			res.setErrorCode("0");
			res.setErrorMessage("");
		}else{
			res.setErrorCode("1");
			res.setErrorMessage("Fail to repeal access_token");
		}
		
		log.info("revocationAccessToken finished");
		return res;
	}
	
	@RequestMapping("/logout")
	private String logout(){
		log.info("logout begin");
		
		log.info("logout finished");
		
		return "logout";
		
	}
}
