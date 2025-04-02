from fastapi import FastAPI, Request, Query, HTTPException
from fastapi.responses import JSONResponse, HTMLResponse
from helpers.proxy_checker import process_proxy
from jinja2 import Environment, FileSystemLoader

app = FastAPI()

env = Environment(loader=FileSystemLoader("templates"))

@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    template = env.get_template("index.html")
    return template.render()

@app.get("/api/v1")
async def check_proxy_url_endpoint(
    request: Request,
    ip: str = Query(None, description="IP address proxy"),
    port: str = Query(None, description="Port proxy")
):
    if ip is None or port is None:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Parameter 'ip' dan 'port' harus diberikan dalam URL.",
                "massage":"Format harus /api/v1?ip=192.168.1.1&port=80"
            },
        )

    try:
        port_number = int(port)
        result = process_proxy(ip, port_number)
        proxyip, message, country_code, asn, country_name, country_flag, http_protocol, org_name, connection_time, latitude, longitude, colo = result

        if proxyip:
            response_data = {
                "ip": ip,
                "port": port_number,
                "proxyip": True,
                "asOrganization": org_name,
                "countryCode": country_code,
                "countryName": country_name,
                "countryFlag": country_flag,
                "asn": asn,
                "colo": colo,
                "httpProtocol": http_protocol,
                "delay": f"{round(connection_time)} ms",
                "latitude": latitude,
                "longitude": longitude,
                "message": message
            }
        else:
            response_data = {
                "ip": ip,
                "port": port_number,
                "proxyip": False,
                "asn": asn,
                "message": message
            }

        return response_data

    except ValueError:
        return JSONResponse(status_code=400, content={"error": "Port harus berupa angka."})
    except Exception as e:
        error_message = f"Terjadi kesalahan server saat memproses proxy {ip}:{port}: {e}"
        print(error_message)
        return JSONResponse(status_code=500, content={"error": error_message})
