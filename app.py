from typing import Dict
import json
import base64
import uuid
import psycopg2
from flask import Flask, render_template, request,jsonify
from cryptography.fernet import Fernet
from webauthn import (
    generate_registration_options,
    verify_registration_response,
    generate_authentication_options,
    verify_authentication_response,
    options_to_json,
)

from webauthn.helpers.structs import (
    AuthenticatorSelectionCriteria,
    UserVerificationRequirement,
    RegistrationCredential,
    AuthenticationCredential,
)
from webauthn.helpers.cose import COSEAlgorithmIdentifier

from .models import Credential, UserAccount

# Create our Flask app


#from sqlalchemy import create_engine


app = Flask(__name__)


# Replace 'your_connection_string' with the actual connection string from ElephantSQL
db_url = 'postgres://ocmhenge:JmAlZ2c-XYCC0W3KHw53JwPwBKGBEtJy@rain.db.elephantsql.com/ocmhenge'
try:
    conn = psycopg2.connect(db_url,options="-c client_encoding=UTF8")
    cursor=conn.cursor()
    print("Connected to the database!")
except psycopg2.DatabaseError as e:
    print("Database Error:", e)
################
#
# RP Configuration
#
################


rp_id = "localhost"
origin = "http://localhost:5000"
rp_name = "Sample RP"


# A simple way to persist credentials by user ID
in_memory_db: Dict[str, UserAccount] = {}


# Register our sample user


# Passwordless assumes you're able to identify the user before performing registration or
# authentication

# A simple way to persist challenges until response verification
current_registration_challenge = None
current_authentication_challenge = None

################
#
# Views
#
################




@app.route("/")
def index():
    return render_template("index.html")




################
#
# Registration
#
################




@app.route("/generate-registration-options", methods=["POST"])
def handler_generate_registration_options():
    global current_registration_challenge
    global username
    global logged_in_user_id
    # Get the username from the request data
    data = request.get_json()
    username = data.get("username")
    logged_in_user_id = str(uuid.uuid4())
    key = Fernet.generate_key()
    key_string = base64.urlsafe_b64encode(key).decode('utf-8')
    print(data)
    print(username)
    print(logged_in_user_id)
    try:
        cursor.execute(
            "INSERT INTO users (id, username, key_value) VALUES (%s, %s,%s)",
            (logged_in_user_id, username,key_string)
        )
        print("inserted data into users table")
        conn.commit()
    except psycopg2.Error as e:
        # Handle the error if the insertion fails
        print(f"Error inserting user data: {e}")
        return {"error": "User data insertion failed "}, 500
   
    cursor.execute("SELECT id, transports FROM credentials WHERE username = %s", (username,))
    existing_credentials = cursor.fetchall()
    if existing_credentials:
        # If credentials exist, exclude them from registration options
        exclude_credentials = [
            {"id": cred[0], "type": "public-key"}
            for cred in existing_credentials
        ]
    else:
        exclude_credentials = []
   
    in_memory_db[logged_in_user_id] = UserAccount(
    id=logged_in_user_id,
    username=username,
    credentials=[],
    )
    print(in_memory_db)




    user = in_memory_db[logged_in_user_id]
    print(user)


    # Use the provided username to generate registration options
    options = generate_registration_options(
        rp_id=rp_id,
        rp_name=rp_name,
        user_id=logged_in_user_id,
        user_name=username,  # Use the provided username
        exclude_credentials=exclude_credentials,
        authenticator_selection=AuthenticatorSelectionCriteria(
            user_verification=UserVerificationRequirement.REQUIRED
        ),
        supported_pub_key_algs=[
            COSEAlgorithmIdentifier.ECDSA_SHA_256,
            COSEAlgorithmIdentifier.RSASSA_PKCS1_v1_5_SHA_256,
        ],
    )


    current_registration_challenge = options.challenge


    return options_to_json(options)


@app.route("/verify-registration-response", methods=["POST"])
def handler_verify_registration_response():
    global current_registration_challenge
    global logged_in_user_id


    body = request.get_data()


    try:
        credential = RegistrationCredential.parse_raw(body)
        verification = verify_registration_response(
            credential=credential,
            expected_challenge=current_registration_challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
        )
    except Exception as err:
        return {"verified": False, "msg": str(err), "status": 400}


    user = in_memory_db[logged_in_user_id]


    new_credential = Credential(
        id=verification.credential_id,
        public_key=verification.credential_public_key,
        sign_count=verification.sign_count,
        transports=json.loads(body).get("transports", []),
    )
    credential_id_text = base64.b64encode(verification.credential_id).decode("utf-8")
    credential_public_key_text = base64.b64encode(verification.credential_public_key).decode("utf-8")
    transports_json = json.dumps(new_credential.transports)
    try:
        cursor.execute(
            "INSERT INTO credentials (id, public_key, sign_count,transports, username) VALUES (%s, %s, %s,%s,%s)",
            (credential_id_text, credential_public_key_text, new_credential.sign_count,transports_json, username)
        )
        conn.commit()
        print("Credential stored in the 'credentials' table.")
    except psycopg2.Error as e:
        # Handle the error if the insertion fails
        print(f"Error inserting credential data: {e}")
        return {"error": "Credential data insertion failed"}, 500


    user.credentials.append(new_credential)
    print(user)
    return {"verified": True}


################
#
# Authentication
#
################


@app.route("/generate-authentication-options", methods=["GET"])
def handler_generate_authentication_options():
    global current_authentication_challenge
    global logged_in_user_id


    user = in_memory_db[logged_in_user_id]
    cursor.execute("SELECT id, transports FROM credentials WHERE username = %s", (username,))
    user_credentials = cursor.fetchall()


    if not user_credentials:
        # If no credentials are found, return an error or handle it as needed
        return {"error": "User has no credentials"}, 400
    #credentials = [
        #{
            #"type": "public-key",
            #"id": cred[0],
            #"transports": json.loads(cred[1]) if cred[1] else [],
        #}
        #for cred in user_credentials
    #]


    options = generate_authentication_options(
        rp_id=rp_id,
        allow_credentials=
        [
            {"type": "public-key", "id": cred.id, "transports": cred.transports}
            for cred in user.credentials
        ],
        user_verification=UserVerificationRequirement.REQUIRED,
    )


    current_authentication_challenge = options.challenge


    return options_to_json(options)




@app.route("/verify-authentication-response", methods=["POST"])
def hander_verify_authentication_response():
    global current_authentication_challenge
    global logged_in_user_id


    body = request.get_data()
    print(body)
    print("hello")
    try:
        credential = AuthenticationCredential.parse_raw(body)
        print("Credential parsed successfully")  
        #credential_id_text2 = base64.urlsafe_b64encode(logged_in_user_id.encode('utf-8')).decode('utf-8').rstrip('=')
        cursor.execute("SELECT public_key, sign_count FROM credentials WHERE username = %s", (username,))
        credential_data = cursor.fetchone()
        print(credential_data)
        print("the row is fetched")


        if not credential_data:
            raise Exception("Could not find corresponding credential in DB")


        credential_public_key = credential_data[0]
        credential_current_sign_count = int(credential_data[1])
        #credential_transports = json.loads(credential_data[3]) if credential_data[3] else []


        print(f"Credential Public Key: {credential_public_key}")
        print(f"Credential Sign Count: {credential_current_sign_count}")
        credential_public_key_decoded = base64.b64decode(credential_public_key)
        #print(f"Credential Transports: {credential_transports}")

        user = in_memory_db[logged_in_user_id]
        user_credential = None
        for _cred in user.credentials:
            if _cred.id == credential.raw_id:
                user_credential = _cred

        if user_credential is None:
            raise Exception("Could not find corresponding public key in DB")

        # Verify the assertion
        verification = verify_authentication_response(
            credential=credential,
            expected_challenge=current_authentication_challenge,
            expected_rp_id=rp_id,
            expected_origin=origin,
            credential_public_key=user_credential.public_key,
            credential_current_sign_count=user_credential.sign_count,
            require_user_verification=True,
        )
    except Exception as err:
        return {"verified": False, "msg": str(err), "status": 400}
    
    user_credential.sign_count = verification.new_sign_count

    # Update our credential's sign count to what the authenticator says it is now
    #user_credential.sign_count = verification.new_sign_count
    #credential_id_text1 = base64.b64encode(verification.credential_id).decode("utf-8")
    #cursor.execute("UPDATE credentials SET sign_count = %s WHERE id = %s", (verification.new_sign_count, credential.raw_id))
    #conn.commit()
    print("hello again")
    return {"verified": True}

#key = Fernet.generate_key()
#cipher_suite = Fernet(key)

@app.route('/encrypt', methods=['POST'])
def encrypt_text():
    try:
        cursor.execute("SELECT key_value FROM users WHERE username = %s", (username,))
        existing_user = cursor.fetchone()
        data = request.json
        text = data['data']  # Access the 'data' key, not 'text'
        cursor.execute("SELECT key_value FROM users WHERE username = %s", (username,))
        key_string = cursor.fetchone()[0]

    # Convert the key_string to bytes
        key = base64.urlsafe_b64decode(key_string.encode('utf-8'))

    # Create a Fernet cipher suite with the user's key
        cipher_suite = Fernet(key)
        encrypted_data = cipher_suite.encrypt(text.encode())
        return jsonify({'encrypted_data': encrypted_data.decode()})
    except KeyError:
        return jsonify({'error': 'Missing or incorrect JSON structure'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/decrypt', methods=['POST'])
def decrypt():
    try:
        data = request.json
        encrypted_text = data['encrypted_data']  # Access the 'encrypted_data' key
        cursor.execute("SELECT key_value FROM users WHERE username = %s", (username,))
        key_string = cursor.fetchone()[0]
        key = base64.urlsafe_b64decode(key_string.encode('utf-8'))
        cipher_suite = Fernet(key)
        decrypted_data = cipher_suite.decrypt(encrypted_text.encode())
        return jsonify({'decrypted_data': decrypted_data.decode()})
    except KeyError:
        return jsonify({'error': 'Missing or incorrect JSON structure'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route("/login-user", methods=["GET"])
def login_user():
    return render_template("login.html")