{
  description = "bio-pipelines on pg_bio and PostgreSQL 18: nix run, no Docker";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";
    pg_bio = {
      url = "github:jonatas/pg_bio";
      inputs.nixpkgs.follows = "nixpkgs";
    };
  };

  outputs =
    {
      self,
      nixpkgs,
      pg_bio,
    }:
    let
      systems = [
        "aarch64-darwin"
        "x86_64-darwin"
        "x86_64-linux"
        "aarch64-linux"
      ];
      forAll = f: nixpkgs.lib.genAttrs systems (system: f (pkgsFor system));
      pkgsFor =
        system:
        import nixpkgs {
          inherit system;
          overlays = [ self.overlays.default ];
        };
    in
    {
      # pg_bio's overlay is part of this one, so applying it to any
      # nixpkgs brings the PostgreSQL that bio-pipelines needs.
      overlays.default = nixpkgs.lib.composeManyExtensions [
        pg_bio.overlays.default
        (final: _prev: {
          bio-pipelines = final.callPackage ./nix/package.nix { };
        })
      ];

      packages = forAll (pkgs: {
        inherit (pkgs) bio-pipelines;
        default = pkgs.bio-pipelines;
      });

      apps = forAll (pkgs: {
        default = {
          type = "app";
          program = nixpkgs.lib.getExe pkgs.bio-pipelines;
        };
      });

      # The whole path offline: init, seed, compile, hypothesis cycle, UI,
      # then base/validate_swarm_web.py against it.
      checks = forAll (pkgs: {
        e2e = pkgs.runCommand "bio-pipelines-e2e" {
          fixtures = ./nix/fixtures;
          nativeBuildInputs = [
            pkgs.bio-pipelines
            pkgs.python3
          ];
        } (builtins.readFile ./nix/e2e.sh);
      });
    };
}
