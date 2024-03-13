

# Spevn-k

# Requirements:

`sudo apt-get update`
`sudo apt-get install wkhtmltopdf`

sudo apt-get install xfonts-75dpi
wget https://github.com/wkhtmltopdf/packaging/releases/download/0.12.6.1-2/wkhtmltox_0.12.6.1-2.jammy_amd64.deb
sudo dpkg -i wkhtmltox_0.12.6.1-2.jammy_amd64.deb
sudo apt --fix-broken install
rm wkhtmltox_0.12.6.1-2.jammy_amd64.deb 

`conda create -n spevnik python=3.11`
`pip install -r requirements.txt`

## Acknowledgments

https://github.com/ptsefton/chordprobook
https://www.chordpro.org/chordpro/support/
