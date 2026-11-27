{
  lib,
  stdenvNoCC,
  makeWrapper,
  python3,
  nodejs,
  curl,
  coreutils,
  gnugrep,
  postgresql-pg_bio,
}:

let
  python = python3.withPackages (
    ps: with ps; [
      flask
      matplotlib
      numpy
      psycopg
      pyyaml
      # The puzzle board tests in base/, run by `test`.
      pytest
      rich
      scipy
    ]
  );
in
stdenvNoCC.mkDerivation {
  pname = "bio-pipelines";
  version = "0.1.0";

  # The app and its data; not output/ (plots and screenshots), the nix
  # files, the Docker files or uv.lock. Each exclusion may be missing, so
  # removing one of those files never breaks this build.
  src = lib.fileset.toSource {
    root = ./..;
    fileset = lib.fileset.difference ./.. (
      lib.fileset.unions [
        (lib.fileset.maybeMissing ../output)
        ../nix
        ../flake.nix
        (lib.fileset.maybeMissing ../flake.lock)
        (lib.fileset.maybeMissing ../Dockerfile)
        (lib.fileset.maybeMissing ../docker-compose.yml)
        (lib.fileset.maybeMissing ../docker-entrypoint.sh)
        (lib.fileset.maybeMissing ../uv.lock)
      ]
    );
  };

  nativeBuildInputs = [ makeWrapper ];

  dontBuild = true;

  installPhase = ''
    runHook preInstall

    share=$out/share/bio-pipelines
    mkdir -p "$share/output" "$out/bin"
    cp -R . "$share"

    install -Dm755 ${./bio-pipelines.sh} "$out/bin/bio-pipelines"
    # nodejs: validate_swarm_web.py runs `node --check` on the pages.
    wrapProgram "$out/bin/bio-pipelines" \
      --set BIO_PIPELINES_SHARE "$share" \
      --prefix PATH : ${
        lib.makeBinPath [
          python
          nodejs
          postgresql-pg_bio
          curl
          coreutils
          gnugrep
        ]
      }

    runHook postInstall
  '';

  meta = {
    description = "Bioprocess compiler and web UI on pg_bio and PostgreSQL 18";
    homepage = "https://github.com/jonatas/bio-pipelines";
    mainProgram = "bio-pipelines";
    platforms = lib.platforms.unix;
  };
}
