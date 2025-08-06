"""
This entrypoint is only used to start a local development server.

For Starlette HTML debug responses, set the DEBUG environment variable to TRUE
"""
from pathlib import Path
import subprocess

import uvicorn

if __name__ == '__main__':
    ssldir = Path(__file__).parents[2] / '.ssl'
    ssldir.mkdir(exist_ok=True)
    certfile = ssldir / 'cert.pem'
    keyfile = ssldir / 'key.pem'
    if not (certfile.exists() and keyfile.exists()):
        argv = [
            'openssl', 'req', '-newkey', 'rsa:4096', '-x509', '-sha512', '-days', '3650', '-nodes',
            '-out', 'cert.pem', '-keyout', 'key.pem',
            '-subj', '/CN=*/',
        ]
        print('Generating self-signed SSL certificate ...')
        try:
            proc = subprocess.run(argv, cwd=ssldir, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, check=True)
            print(proc.stdout.decode())
        except subprocess.CalledProcessError as ex:
            print(f'Error: {ex.output.decode()}')
            print(ex)

    uvicorn.run('app:app', ssl_certfile=str(certfile), ssl_keyfile=str(keyfile), port=5000, reload=True)
