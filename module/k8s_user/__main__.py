import os
import sys
import argparse
import kubernetes
from kubernetes import client, config
from .user import CSRK8sUser, TokenK8sUser


def main(args=None):

    parser = argparse.ArgumentParser(
        prog="k8s_user", description="Create K8S User", epilog=""
    )

    subparsers = parser.add_subparsers(help="", dest="user_type")


    parser.add_argument(
        "--kubeconfig",
        dest="in_kubeconfig",
        help=(
            "This is the name of the kubeconfig that will be used to create "
            "the new user. This kubeconfig requires permissions to create, view, "
            "and approve k8s CSR resources. If not specified, the default kubeconfig "
            "will be used."
        ),
        default=None,
    )

    parser.add_argument(
        "-d",
        "--out-dir",
        dest="out_directory",
        help=(
            "If passed, the newly created public key, CSR, and cert files "
            "will be saved to this location in PEM format. This is in case "
            "you want to have these creds available in PEM format in "
            "addition to having the creds embedded in the kubeconfig file."
        ),
        default=None,
    )
    parser_csr = subparsers.add_parser("csr", help="CSR User Generator")

    parser_csr.add_argument(
        "-k",
        "--out-kubeconfig",
        dest="out_kubeconfig",
        help=(
            "Output kubeconfig file path. A new kubeconfig "
            "file will be generated at this location with "
            "the credentials needed to login as the specified user."
        ),
    )

    parser_csr.add_argument(
        "--out-kubeconfig-context-name",
        dest="out_context",
        help=(
            "When used with the --out-kubeconfig option, this is the "
            "name of the kubeconfig context that will be associated with the user."
        ),
        default="default",
    )

    parser_csr.add_argument(
        "--out-kubeconfig-cluster-name",
        dest="out_cluster",
        help=(
            "When used with the --out-kubeconfig option, this is the "
            "name of the kubeconfig cluster that will be associated with the user"
        ),
        default="default",
    )

    parser_csr.add_argument(
        "name",
        nargs="?",
        help=(
            "The name of the new user to create, as well as the name "
            "of the k8s resource that will be attached to this user."
        ),
    )

    parser_csr.add_argument(
        "--in-key",
        dest="in_key",
        help=(
            "Optionally pass in a filesystem path to an existing RSA key in PEM "
            "format instead of generating a new key."
        ),
        default=None,
    )

    parser_csr.add_argument(
        "--in-key-password",
        dest="in_key_password",
        help=(
            "If --in-key is passed, and if that key has a password set, "
            "this is the password to decrypt that key."
        ),
        default=None,
    )

    parser_csr.add_argument(
        "--in-csr",
        dest="in_csr",
        help=(
            "Optonally pass in a filesystem path to an existing CSR file in PEM "
            "format. This requires the --in-key argument and requires that "
            "the CSR belongs to the KEY (the modulus match)."
        ),
        default=None,
    )

    parser_token = subparsers.add_parser("sa", help="SA Token User Generator")
    parser_token.add_argument(
        "-k",
        "--out-kubeconfig",
        dest="out_kubeconfig",
        help=(
            "Output kubeconfig file path. A new kubeconfig "
            "file will be generated at this location with "
            "the credentials needed to login as the specified user."
        ),
    )

    parser_token.add_argument(
        "--out-kubeconfig-context-name",
        dest="out_context",
        help=(
            "When used with the --out-kubeconfig option, this is the "
            "name of the kubeconfig context that will be associated with the user."
        ),
        default="default",
    )

    parser_token.add_argument(
        "--out-kubeconfig-cluster-name",
        dest="out_cluster",
        help=(
            "When used with the --out-kubeconfig option, this is the "
            "name of the kubeconfig cluster that will be associated with the user"
        ),
        default="default",
    )

    parser_token.add_argument(
        "name",
        nargs="?",
        help=(
            "The name of the new user to create, as well as the name "
            "of the Service Account resource that will be attached to this user."
        ),
    )

    parser_token.add_argument(
        "namespace",
        nargs="?",
        default="default",
        help=("The namespace of the service account associated with the user."),
    )

    args = parser.parse_args()
    print(args)

    # sys.exit(1)

    if not args.user_type:
        print("user_type argument must be specified")
        sys.exit(1)

    if not args.name:
        print("Name argument must be specified")
        sys.exit(1)

    out_directory = args.out_directory

    if args.out_kubeconfig:
        out_kubeconfig = args.out_kubeconfig
    else:
        out_kubeconfig = f"{args.name}-kubeconfig.yaml"
        if out_directory:
            out_kubeconfig = os.path.join(out_directory, out_kubeconfig)

    if os.path.isfile(out_kubeconfig):
        print("kubeconfig file exists already at this location")
        sys.exit(1)

    api_client = config.new_client_from_config(config_file=args.in_kubeconfig)

    try:
        inputs_common = dict(
            cluster_name=args.out_cluster,
            context_name=args.out_context,
            out_kubeconfig=out_kubeconfig,
        )
        if args.user_type == "csr":
            user = CSRK8sUser(name=args.name,)

            inputs = {
                **dict(
                    creds_dir=out_directory,
                    in_key=args.in_key,
                    in_key_password=args.in_key_password,
                    in_csr=args.in_csr,
                ),
                **inputs_common,
            }
        elif args.user_type == "sa":
            user = TokenK8sUser(name=args.name,)
            inputs = {**dict(namespace=args.namespace,), **inputs_common}
        else:
            raise Exception("Must include a user_type as argument")
        user.create(api_client, inputs)
    except Exception as e:
        raise
        print(f"{e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
