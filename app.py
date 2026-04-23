from flask import Flask, render_template, request, send_file, jsonify
from pathlib import Path
from contextlib import suppress
import os
import socket

try:
    from zeroconf import Zeroconf, ServiceInfo
except ImportError:
    Zeroconf = None
    ServiceInfo = None

app = Flask(__name__, static_folder='static', template_folder='templates')

# Configuration
UPLOAD_FOLDER = Path.home() / 'FileTransfers'
UPLOAD_FOLDER.mkdir(exist_ok=True)
app.config['UPLOAD_FOLDER'] = str(UPLOAD_FOLDER)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024 * 1024  # 10GB max
HOST = os.getenv('FILE_TRANSFER_HOST', '0.0.0.0')
PORT = int(os.getenv('FILE_TRANSFER_PORT', '5000'))
SERVICE_NAME = os.getenv('FILE_TRANSFER_NAME', 'File Transfer Hub')
HOSTNAME = os.getenv('FILE_TRANSFER_HOSTNAME', 'file-transfer.local')


def ensure_fqdn(name):
    """Ensure a hostname ends with a trailing dot for zeroconf."""
    return name if name.endswith('.') else f'{name}.'


def get_local_ip():
    """Get the local IP address of this device."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def register_mdns_service(ip_address, port):
    """Advertise the server on the local network with mDNS when available."""
    if Zeroconf is None or ServiceInfo is None:
        return None, 'zeroconf not installed'

    try:
        addresses = [socket.inet_aton(ip_address)]
    except OSError:
        return None, 'invalid local IP address'

    zeroconf = Zeroconf()
    service_type = '_http._tcp.local.'
    service_name = f'{SERVICE_NAME}.{service_type}'
    info = ServiceInfo(
        service_type,
        service_name,
        addresses=addresses,
        port=port,
        server=ensure_fqdn(HOSTNAME),
    )

    try:
        zeroconf.register_service(info)
    except Exception:
        with suppress(Exception):
            zeroconf.close()
        raise

    return zeroconf, f'http://{HOSTNAME}:{port}'


@app.route('/')
def index():
    """Serve the main page."""
    return render_template('index.html')


@app.route('/api/files', methods=['GET'])
def list_files():
    """List all files in the upload folder."""
    try:
        files = []
        for file_path in UPLOAD_FOLDER.iterdir():
            if file_path.is_file():
                files.append({
                    'name': file_path.name,
                    'size': file_path.stat().st_size,
                    'size_display': format_size(file_path.stat().st_size),
                })
        files.sort(key=lambda x: x['name'])
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/upload', methods=['POST'])
def upload_file():
    """Handle file uploads."""
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file provided'}), 400
        
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No file selected'}), 400
        
        # Save file
        file_path = UPLOAD_FOLDER / file.filename
        file.save(str(file_path))
        
        return jsonify({
            'success': True,
            'message': f'File "{file.filename}" uploaded successfully',
            'filename': file.filename
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/download/<filename>')
def download_file(filename):
    """Download a file."""
    try:
        file_path = UPLOAD_FOLDER / filename
        
        # Security: prevent directory traversal
        if not file_path.resolve().is_relative_to(UPLOAD_FOLDER.resolve()):
            return jsonify({'error': 'Invalid file'}), 403
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        return send_file(str(file_path), as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/delete/<filename>', methods=['DELETE'])
def delete_file(filename):
    """Delete a file."""
    try:
        file_path = UPLOAD_FOLDER / filename
        
        # Security: prevent directory traversal
        if not file_path.resolve().is_relative_to(UPLOAD_FOLDER.resolve()):
            return jsonify({'error': 'Invalid file'}), 403
        
        if not file_path.exists():
            return jsonify({'error': 'File not found'}), 404
        
        file_path.unlink()
        return jsonify({'success': True, 'message': f'File "{filename}" deleted'})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/api/info')
def get_info():
    """Get server info."""
    return jsonify({
        'ip': get_local_ip(),
        'port': PORT,
        'hostname': HOSTNAME,
        'upload_folder': str(UPLOAD_FOLDER),
        'storage_free': get_folder_size(UPLOAD_FOLDER),
    })


def format_size(bytes_size):
    """Format bytes to human readable size."""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def get_folder_size(path):
    """Calculate folder size."""
    total = 0
    try:
        for entry in path.iterdir():
            if entry.is_file():
                total += entry.stat().st_size
    except Exception:
        pass
    return format_size(total)


if __name__ == '__main__':
    ip = get_local_ip()
    zeroconf = None
    mdns_url = None

    try:
        zeroconf, mdns_url = register_mdns_service(ip, PORT)
    except Exception as exc:
        print(f'⚠️  mDNS advertising failed: {exc}')

    print(f"\n File Transfer Server Running")
    print(f" Access from other devices at: http://{ip}:{PORT}")
    if mdns_url:
        print(f" Short LAN name: {mdns_url}")
    else:
        print(f" Short LAN name: http://{HOSTNAME}:{PORT} (set up local DNS or mDNS support)")
    print(f" Files stored in: {UPLOAD_FOLDER}\n")

    try:
        app.run(host=HOST, port=PORT, debug=False, use_reloader=False)
    finally:
        if zeroconf is not None:
            with suppress(Exception):
                zeroconf.close()
