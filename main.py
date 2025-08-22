from fastapi import FastAPI, Query
from fastapi.responses import JSONResponse
from helpers.proxy_checker import process_proxy

app = FastAPI()

@app.get("/api/v1/check")
async def check_proxy_url_endpoint(
    proxyip: str = Query(None, description="Proxy in format IP:PORT")
):
    if proxyip is None:
        return JSONResponse(
            status_code=400,
            content={
                "error": "Parameter 'proxyip' must be provided in the URL.",
                "example": "/api/v1/check?proxyip=1.1.1.1:443 or /api/v1/check?proxyip=8.8.8.8"
            },
        )

    try:
        parts = proxyip.split(':')
        ip = parts[0]
        port = parts[1] if len(parts) > 1 else "443"
        
        if not ip:
            raise ValueError("IP address cannot be empty.")

    except (ValueError, IndexError):
        return JSONResponse(
            status_code=400,
            content={
                "error": "Invalid 'proxyip' format.",
                "expected_format": "IP:PORT"
            }
        )

    try:
        port_number = int(port)
        result = process_proxy(ip, port_number)
        is_alive, message, country_code, asn, country_name, country_flag, http_protocol, org_name, connection_time, latitude, longitude, colo = result

        if is_alive:
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
                "ping": f"{round(connection_time)} ms",
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
        return JSONResponse(status_code=400, content={"error": "Port must be a number."})
    except Exception as e:
        error_message = f"An internal server error occurred while processing the proxy {ip}:{port}: {e}"
        print(error_message)
        return JSONResponse(status_code=500, content={"error": error_message})
