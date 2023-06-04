# ERSMS_beer_hangout_app
## How to set up local development environment
Start Firestore emulator.
```
gcloud emulators firestore start
```
Export FIRESTORE_EMULATOR_HOST variable.
Ensure that you have ../client_secret.json file.
Run local development server.
```
ENV=local python3 main.py
```
## How to build and run docker image
Build
```
docker build -t postspot-userservice .
```
Run
```
docker run -e ENV=development -e FIRESTORE_EMULATOR_HOST=[::1]:8726 -e GOOGLE_AUTH_CLIENT_SECRET=$GOOGLE_AUTH_CLIENT_SECRET -p 5000:5000 postspot-userservice
```