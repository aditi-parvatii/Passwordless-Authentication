# Password-less Login System 
This is a sample web application that demonstrates the usage of WebAuthn (Web Authentication) for user registration and authentication. WebAuthn is a modern web standard for secure and passwordless authentication. It is believed to be a lot safer as compared to the other authentication techniques which are out there. 

### Features:
Postgres SQL: We will be interacting with the database which is hosted on Elephant SQL to persist credential information.
FLASK: Used Flask framework on the server side for the web application
WebAuthn: Software library that provides a programming interface for web applications to integrate strong, passwordless authentication mechanisms into their user authentication workflows

Python Version:(>=3.8)


## API DOCUMENTATION

##### POST /generate-registration-options 
Relying party generates registration options which is then sent to the client. 
  
###### Request & Response headers  
Content-Type: application/json  

###### Request Body
The request body should include the following JSON data:

username (string, required): The username of the user for whom registration options should be generated.

###### Body  
```  
{  
     "username": "xusername",
}  
```

###### Success Response  
* HTTP/1.1 200 OK
* Response Body: 
    The response will contain a JSON object representing the registration options, which includes challenge data and other registration-related information.


##### POST /verify-registration-options 
Verify the registration response from a user during the registration process. It verifies the authenticity of the user's registration credentials and stores them in the database if the verification is successful. 
  
###### Request & Response headers  
Content-Type: application/json  

###### Request Body
The request body should contain the binary data representing the registration response credentials.
This the response given out by then authenticator. 

###### Response Body 
```  
{
    "verified": true
} 
```

###### Success Response  
* HTTP/1.1 200 OK


##### GET /generate-authentication-options
Relying party generates authentication options for a user based on their stored credentials. It is used for user authentication with a focus on web authentication using public keys. 
  
###### Request & Response headers  
Content-Type: application/json  

###### Response Body
The response will contain a JSON object representing the authentication options, which includes a challenge and a list of allowed credentials.

challenge (string): A random challenge string used in the authentication process.
allowCredentials (array of objects): An array of credential objects that are allowed for authentication. Each credential object has the following properties:
type (string): The type of the credential (e.g., "public-key").
id (string): The unique identifier of the credential.
transports (array of strings, optional): An array of transport methods supported by the credential.

###### Success Response  
* HTTP/1.1 200 OK

##### POST /verify-authentication-response
This endpoint is used to verify the authentication response received from a user during the authentication process. It verifies the authenticity of the user's credentials and checks whether the response is valid for the given challenge and user.
  
###### Request & Response headers  
Content-Type: application/json  

###### Request Body
The request body should contain the binary data representing the authentication response. The binary data is typically provided by the client-side browser or device after a user successfully authenticates.

###### Response Body 
The response will contain a JSON object indicating whether the authentication response was successfully verified.
verified (boolean): Indicates whether the authentication response was successfully verified.

```  
{
    "verified": true
} 
```

###### Success Response  
* HTTP/1.1 200 OK
