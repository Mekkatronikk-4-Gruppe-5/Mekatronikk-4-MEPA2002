# Pi Drift og Vedlikehold

## Bunnlinje

Denne siden er for driftsting på Raspberry Pi: diskplass, Docker-opprydding,
CPU governor, temperatur og throttling. Dette er ikke vanlig robot-bringup, men
nyttig når Pi-en blir treg, bygger feiler, eller Docker bruker for mye lagring.

Kjør kommandoene på **Pi-host**, ikke inne i Docker-containeren, med mindre noe
annet står eksplisitt.

## Docker Build-Policy

`make build` bygger hele Docker-imaget på nytt. Det er tregt, bruker mye
disk/cache, og skal ikke være en vanlig del av robotkjøring.

Kjør vanligvis dette etter kodeendringer:

```bash
make ws
```

Kjør `make build` bare når du faktisk har endret runtime-miljøet:

- [`docker/Dockerfile`](../../docker/Dockerfile)
- apt-avhengigheter
- pip-avhengigheter
- base image
- systembiblioteker som må finnes inne i containeren

Ikke kjør `make build` bare fordi du har endret:

- ROS Python-kode
- launch-filer
- YAML-konfig
- dokumentasjon
- Arduino-sketcher

Hvis du er usikker: prøv `make ws` først. Bruk `make build` først når feilen
handler om manglende pakker eller endret Docker-runtime.

Docker Compose Build
--------------------

`make build` bruker vanlig Compose-build:

```bash
docker compose build
```

[`compose.yml`](../../compose.yml) bruker repo-roten som build-context, men
repoets [`.dockerignore`](../../.dockerignore) slipper bare gjennom `docker/`.
Da sendes ikke workspace, modeller, dokumentasjon, git-historikk eller gamle
buildmapper inn i Docker-builden.

`docker/Dockerfile` bruker ikke apt/pip cache-mounts. Pi-en har raskt nettverk,
men tregt SD-kort, så default build prioriterer lavere disk-I/O og mindre
cache-vekst over å cache nedlastede pakker. Vanlig Docker layer-cache beholdes
likevel mellom builds.

## Docker Diskplass

### Først: se hva som tar plass

```bash
df -h
docker system df
docker system df -v
```

`df -h` viser ledig plass på `/`. `docker system df` viser Docker-kategorier:

| Kategori | Hva det er | Typisk rydding |
|---|---|---|
| `Images` | Ferdige Docker images, inkludert gamle/tag-løse images | `docker image prune -f` eller `docker image prune -af` |
| `Build Cache` | Mellomlag Docker bruker for raskere neste build | `docker builder prune -af` |
| `Containers` | Stoppede/kjørende containere | `docker container prune -f` |
| `Local Volumes` | Docker-volumer med data | Sjekk først. Ikke slett blindt. |

Viktig: `docker system prune -af` er bred rydding. Den kan slette ubrukte images
og build-cache. Ikke bruk den hvis målet er å beholde build-cache.

### Behold build-cache, fjern gamle images

Bruk dette når du skal bygge på nytt og vil beholde cache:

```bash
cd ~/Mekatronikk-4-MEPA2002
docker compose down --remove-orphans
docker container prune -f
docker image prune -f
df -h
docker system df
```

`docker image prune -f` fjerner bare dangling/tag-løse images, ofte gamle
`<none>` images etter ny build. Den skal ikke slette build-cache.

Hvis du vil fjerne alle images som ikke er i bruk av en container, men fortsatt
beholde build-cache:

```bash
docker image prune -af
```

Det kan fjerne `mekk4/ros2-jazzy-dev:local` hvis ingen container bruker imaget.
Da må `make build` bygge/laste image igjen, men Docker build-cache beholdes.

### Slett build-cache

Bruk bare når cache tar for mye plass, eller når du vil tvinge en fresh build:

```bash
docker builder prune -af
```

Konsekvens: neste `make build` blir tregere fordi Docker må bygge lag på nytt.

### Slett både images og build-cache

Bruk bare når du faktisk vil rydde hardt:

```bash
docker system prune -af
docker builder prune -af
```

`docker system prune -af` sletter ubrukte images, stoppede containere, ubrukte
nettverk og kan slette build-cache. `docker builder prune -af` sletter
build-cache eksplisitt.

### Rydd apt cache på Pi-host

```bash
sudo apt clean
```

Fjerner nedlastede `.deb`-pakker fra Pi-host. Installerte pakker fjernes ikke.

### Sjekk repo-mapper

```bash
du -h --max-depth=1 ~/Mekatronikk-4-MEPA2002 | sort -h
```

Vanlige store repo-mapper er `build/`, `install/`, `log/` og `.ultralytics/`.

## Workspace-Rydding

### Fjern `build/` og `log/`

```bash
rm -rf ~/Mekatronikk-4-MEPA2002/build ~/Mekatronikk-4-MEPA2002/log
```

Fjerner lokale colcon build- og logmapper.

Bruk når:

- workspace-build oppfører seg rart.
- du vil frigjøre plass uten å slette installasjonen.

Konsekvens:

- Neste build må kompilere/generere mer på nytt.
- `install/` beholdes, så eksisterende installasjon kan fortsatt fungere.

Risiko:

- Lav, så lenge pathen er riktig.
- Dette er en destruktiv kommando for genererte filer. Kontroller pathen før du
  kjører den.

### Fjern `install/`

```bash
rm -rf ~/Mekatronikk-4-MEPA2002/install
```

Fjerner installert ROS workspace.

Bruk når:

- du trenger mer plass enn `build/` og `log/` frigjør.
- installasjonen er stale eller inkonsistent.
- `source install/setup.bash` gir gamle pakker/launch-filer.

Konsekvens:

- ROS-pakkene i workspace er ikke tilgjengelige før du bygger på nytt.
- Kjør etterpå:

```bash
make ws
```

Risiko:

- Moderat. Ikke kildekode, men du må bygge workspace på nytt.

## Ryddeoppskrifter

### Før ny Docker-build, behold cache

```bash
cd ~/Mekatronikk-4-MEPA2002
df -h
docker system df
docker compose down --remove-orphans
docker container prune -f
docker image prune -f
df -h
docker system df
```

### Lite diskplass, cache kan slettes

```bash
cd ~/Mekatronikk-4-MEPA2002
docker compose down --remove-orphans
docker system prune -af
docker builder prune -af
sudo apt clean
df -h
docker system df
```

## CPU Governor og Ytelse

### Se aktiv CPU-policy

```bash
cpupower frequency-info
```

Viser tilgjengelige CPU governors, frekvensområde og aktiv policy.

Bruk når:

- YOLO eller Nav2 virker tregt.
- du vil sjekke om Pi-en kjører i powersave/ondemand/performance.

Hvis `cpupower` mangler, installer på Pi-host:

```bash
sudo apt install linux-cpupower
```

### Sett maks ytelse

```bash
sudo cpupower frequency-set -g performance
```

Setter CPU governor til `performance`. Det gjør at CPU-en prøver å holde høyere
klokkefrekvens.

Bruk når:

- du tester YOLO/FPS.
- du kjører Nav2 og perception samtidig.
- du vil redusere latency under demo/test.

Konsekvens:

- Høyere strømforbruk.
- Mer varme.
- Større risiko for throttling hvis kjøling er dårlig.

### Verifiser aktiv governor

```bash
cat /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
```

Printer aktiv governor for CPU0, for eksempel:

```text
performance
```

Bruk etter `frequency-set` for å bekrefte at endringen faktisk slo inn.

### Sett tilbake dynamisk modus

```bash
sudo cpupower frequency-set -g ondemand
```

Setter CPU tilbake til dynamisk governor. Dette er bedre når roboten ikke trenger
maks ytelse hele tiden.

Bruk når:

- demo/test er ferdig.
- Pi-en blir varm.
- du kjører på batteri og vil spare strøm.

## Temperatur og Throttling

### Live overvåking

```bash
watch -n1 'vcgencmd measure_temp; vcgencmd measure_clock arm; vcgencmd get_throttled'
```

Kjører tre Pi-kommandoer hvert sekund:

| Del | Betydning |
|---|---|
| `vcgencmd measure_temp` | CPU/GPU-temperatur |
| `vcgencmd measure_clock arm` | aktuell ARM CPU-klokke |
| `vcgencmd get_throttled` | throttling/undervoltage-status |

Bruk når:

- YOLO FPS faller over tid.
- Pi-en blir fysisk varm.
- systemet virker raskt etter boot, men tregere etter noen minutter.

### Tolke `get_throttled`

Eksempel:

```text
throttled=0x0
```

`0x0` betyr ingen aktiv eller historisk throttling siden boot.

Hvis verdien ikke er `0x0`, har Pi-en hatt undervoltage, throttling eller
temperaturbegrensning. Da bør du sjekke:

- strømforsyning
- USB-belastning
- kjøling
- CPU governor
- om YOLO-oppløsning/FPS er for høy

## Praktisk Ytelsesrekkefølge

Hvis perception eller Nav2 er tregt:

1. Sjekk temperatur og throttling.
2. Sett `performance` governor midlertidig.
3. Reduser kamera `fps`, `width`, `height` eller YOLO `imgsz` i
   [`camera_params.yaml`](../../config/camera_params.yaml).
4. Kjør `make camera-reload` for kamera/encoder-tuning.
5. Full restart av `make pi-bringup` hvis du endrer width/height/porter.
