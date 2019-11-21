import os
import docker
import tarfile

client = docker.from_env()
client.login(os.environ.get('DOCKER_USERNAME'), os.environ.get('DOCKER_PASSWORD'))

container = client.containers.run(image="jwonsil/jwons-llvis-3", detach=True, environment=["PASSWORD=llvis"], ports={'8787':'8787'})

result = container.exec_run("find /home/rstudio -name 'prov_data'")
f = open('./sh_bin.tar', 'wb')
bits, stat = container.get_archive(result[1].decode("ascii").strip())

for chunk in bits:
    f.write(chunk)

f.close()

tar = tarfile.open("./sh_bin.tar", "r:")
tar.extractall()
tar.close()

jsonFiles = []

for file in os.listdir("./prov_data"):
    if file.endswith(".json"):
        jsonFiles.append(file)

container.kill()