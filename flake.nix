{
  description = "Dev environment for voyager-keymap (ZSA Voyager + Moonlander QMK firmware)";

  inputs.nixpkgs.url = "github:NixOS/nixpkgs/nixos-26.05";

  outputs = { self, nixpkgs }:
    let
      systems = [ "x86_64-linux" "aarch64-linux" "x86_64-darwin" "aarch64-darwin" ];
      forAllSystems = f: nixpkgs.lib.genAttrs systems f;
    in {
      devShells = forAllSystems (system:
        let pkgs = import nixpkgs { inherit system; };
        in {
          default = pkgs.mkShell {
            packages = [
              pkgs.qmk
              pkgs.gcc-arm-embedded
              pkgs.dfu-util
            ];
            # qmk's python is missing the appdirs dependency in nixpkgs;
            # wire it in directly instead of patching PYTHONPATH per-script.
            env.PYTHONPATH = "${pkgs.python3Packages.appdirs}/${pkgs.python3.sitePackages}";
          };
        });
    };
}
