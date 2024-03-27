$pyinstallerCommand = "pyinstaller --onefile --windowed -i '.\resources\quickparse.ico' --add-data '.\resources\quickparse.ico;.' --clean '.\qp_gui.py'"
Start-Process -FilePath "powershell.exe" -ArgumentList "-Command", $pyinstallerCommand -NoNewWindow -Wait

$cert = New-SelfSignedCertificate -DnsName "Brendan Olson" -CertStoreLocation "Cert:\CurrentUser\My" -Type CodeSigning -TextExtension @("2.5.29.37={text}1.3.6.1.5.5.7.3.3") -Subject "CN=Brendan Olson"
Set-AuthenticodeSignature -FilePath ".\dist\qp_gui.exe" -Certificate $cert -TimestampServer "http://timestamp.digicert.com"