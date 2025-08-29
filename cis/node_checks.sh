#!/bin/bash

# CIS Kubernetes Benchmark v1.9 - Worker Node Security Configuration Checks
# Based on node.yml from kube-bench project

set -e

# Default values for variables (these should be adjusted based on your environment)
kubeletsvc=${kubeletsvc:-"/etc/systemd/system/kubelet.service.d/10-kubeadm.conf"}
proxykubeconfig=${proxykubeconfig:-"/etc/kubernetes/proxy.conf"}
kubeletkubeconfig=${kubeletkubeconfig:-"/etc/kubernetes/kubelet.conf"}
kubeletcafile=${kubeletcafile:-"/etc/kubernetes/pki/ca.crt"}
kubeletconf=${kubeletconf:-"/var/lib/kubelet/config.yaml"}
kubeletbin=${kubeletbin:-"kubelet"}
proxybin=${proxybin:-"kube-proxy"}

echo "CIS Kubernetes Benchmark v1.9 - Worker Node Security Configuration Checks"
echo "========================================================================="

# Function to print section headers
print_section() {
    echo ""
    echo "-----------------------------------------------------------------"
    echo "$1"
    echo "-----------------------------------------------------------------"
}

# Function to print check results
print_check() {
    echo "[$1] $2"
}

# Function to print remediation
print_remediation() {
    echo "Remediation:"
    echo "$1"
    echo ""
}

# 4.1 Worker Node Configuration Files
print_section "4.1 Worker Node Configuration Files"

# 4.1.1 Ensure that the kubelet service file permissions are set to 600 or more restrictive
print_check "4.1.1" "Ensure that the kubelet service file permissions are set to 600 or more restrictive"
if test -e "$kubeletsvc"; then
    permissions=$(stat -c %a "$kubeletsvc" 2>/dev/null || echo "unknown")
    if [[ "$permissions" =~ ^[0-6][0-4][0-4]$ ]]; then
        echo "PASS: kubelet service file permissions are $permissions"
    else
        echo "FAIL: kubelet service file permissions are $permissions"
    fi
else
    echo "INFO: kubelet service file not found at $kubeletsvc"
fi
print_remediation "Run the below command (based on the file location on your system) on the each worker node.
For example, chmod 600 $kubeletsvc"

# 4.1.2 Ensure that the kubelet service file ownership is set to root:root
print_check "4.1.2" "Ensure that the kubelet service file ownership is set to root:root"
if test -e "$kubeletsvc"; then
    ownership=$(stat -c %U:%G "$kubeletsvc" 2>/dev/null || echo "unknown")
    if [[ "$ownership" == "root:root" ]]; then
        echo "PASS: kubelet service file ownership is $ownership"
    else
        echo "FAIL: kubelet service file ownership is $ownership"
    fi
else
    echo "INFO: kubelet service file not found at $kubeletsvc"
fi
print_remediation "Run the below command (based on the file location on your system) on the each worker node.
For example,
chown root:root $kubeletsvc"

# 4.1.3 If proxy kubeconfig file exists ensure permissions are set to 600 or more restrictive
print_check "4.1.3" "If proxy kubeconfig file exists ensure permissions are set to 600 or more restrictive"
if test -e "$proxykubeconfig"; then
    permissions=$(stat -c %a "$proxykubeconfig" 2>/dev/null || echo "unknown")
    if [[ "$permissions" =~ ^[0-6][0-4][0-4]$ ]]; then
        echo "PASS: proxy kubeconfig file permissions are $permissions"
    else
        echo "FAIL: proxy kubeconfig file permissions are $permissions"
    fi
else
    echo "INFO: proxy kubeconfig file not found at $proxykubeconfig"
fi
print_remediation "Run the below command (based on the file location on your system) on the each worker node.
For example,
chmod 600 $proxykubeconfig"

# 4.1.4 If proxy kubeconfig file exists ensure ownership is set to root:root
print_check "4.1.4" "If proxy kubeconfig file exists ensure ownership is set to root:root"
if test -e "$proxykubeconfig"; then
    ownership=$(stat -c %U:%G "$proxykubeconfig" 2>/dev/null || echo "unknown")
    if [[ "$ownership" == "root:root" ]]; then
        echo "PASS: proxy kubeconfig file ownership is $ownership"
    else
        echo "FAIL: proxy kubeconfig file ownership is $ownership"
    fi
else
    echo "INFO: proxy kubeconfig file not found at $proxykubeconfig"
fi
print_remediation "Run the below command (based on the file location on your system) on the each worker node.
For example, chown root:root $proxykubeconfig"

# 4.1.5 Ensure that the --kubeconfig kubelet.conf file permissions are set to 600 or more restrictive
print_check "4.1.5" "Ensure that the --kubeconfig kubelet.conf file permissions are set to 600 or more restrictive"
if test -e "$kubeletkubeconfig"; then
    permissions=$(stat -c %a "$kubeletkubeconfig" 2>/dev/null || echo "unknown")
    if [[ "$permissions" =~ ^[0-6][0-4][0-4]$ ]]; then
        echo "PASS: kubelet kubeconfig file permissions are $permissions"
    else
        echo "FAIL: kubelet kubeconfig file permissions are $permissions"
    fi
else
    echo "INFO: kubelet kubeconfig file not found at $kubeletkubeconfig"
fi
print_remediation "Run the below command (based on the file location on your system) on the each worker node.
For example,
chmod 600 $kubeletkubeconfig"

# 4.1.6 Ensure that the --kubeconfig kubelet.conf file ownership is set to root:root
print_check "4.1.6" "Ensure that the --kubeconfig kubelet.conf file ownership is set to root:root"
if test -e "$kubeletkubeconfig"; then
    ownership=$(stat -c %U:%G "$kubeletkubeconfig" 2>/dev/null || echo "unknown")
    if [[ "$ownership" == "root:root" ]]; then
        echo "PASS: kubelet kubeconfig file ownership is $ownership"
    else
        echo "FAIL: kubelet kubeconfig file ownership is $ownership"
    fi
else
    echo "INFO: kubelet kubeconfig file not found at $kubeletkubeconfig"
fi
print_remediation "Run the below command (based on the file location on your system) on the each worker node.
For example,
chown root:root $kubeletkubeconfig"

# 4.1.7 Ensure that the certificate authorities file permissions are set to 600 or more restrictive
print_check "4.1.7" "Ensure that the certificate authorities file permissions are set to 600 or more restrictive"
CAFILE=$(ps -ef | grep kubelet | grep -v apiserver | grep -- --client-ca-file= | awk -F '--client-ca-file=' '{print $2}' | awk '{print $1}' | uniq)
if test -z "$CAFILE"; then 
    CAFILE="$kubeletcafile"
fi

if test -e "$CAFILE"; then
    permissions=$(stat -c %a "$CAFILE" 2>/dev/null || echo "unknown")
    if [[ "$permissions" =~ ^[0-6][0-4][0-4]$ ]]; then
        echo "PASS: CA file permissions are $permissions"
    else
        echo "FAIL: CA file permissions are $permissions"
    fi
else
    echo "INFO: CA file not found at $CAFILE"
fi
print_remediation "Run the following command to modify the file permissions of the
--client-ca-file chmod 600 <filename>"

# 4.1.8 Ensure that the client certificate authorities file ownership is set to root:root
print_check "4.1.8" "Ensure that the client certificate authorities file ownership is set to root:root"
if test -e "$CAFILE"; then
    ownership=$(stat -c %U:%G "$CAFILE" 2>/dev/null || echo "unknown")
    if [[ "$ownership" == "root:root" ]]; then
        echo "PASS: CA file ownership is $ownership"
    else
        echo "FAIL: CA file ownership is $ownership"
    fi
else
    echo "INFO: CA file not found at $CAFILE"
fi
print_remediation "Run the following command to modify the ownership of the --client-ca-file.
chown root:root <filename>"

# 4.1.9 If the kubelet config.yaml configuration file is being used validate permissions set to 600 or more restrictive
print_check "4.1.9" "If the kubelet config.yaml configuration file is being used validate permissions set to 600 or more restrictive"
if test -e "$kubeletconf"; then
    permissions=$(stat -c %a "$kubeletconf" 2>/dev/null || echo "unknown")
    if [[ "$permissions" =~ ^[0-6][0-4][0-4]$ ]]; then
        echo "PASS: kubelet config file permissions are $permissions"
    else
        echo "FAIL: kubelet config file permissions are $permissions"
    fi
else
    echo "INFO: kubelet config file not found at $kubeletconf"
fi
print_remediation "Run the following command (using the config file location identified in the Audit step)
chmod 600 $kubeletconf"

# 4.1.10 If the kubelet config.yaml configuration file is being used validate file ownership is set to root:root
print_check "4.1.10" "If the kubelet config.yaml configuration file is being used validate file ownership is set to root:root"
if test -e "$kubeletconf"; then
    ownership=$(stat -c %U:%G "$kubeletconf" 2>/dev/null || echo "unknown")
    if [[ "$ownership" == "root:root" ]]; then
        echo "PASS: kubelet config file ownership is $ownership"
    else
        echo "FAIL: kubelet config file ownership is $ownership"
    fi
else
    echo "INFO: kubelet config file not found at $kubeletconf"
fi
print_remediation "Run the following command (using the config file location identified in the Audit step)
chown root:root $kubeletconf"

# 4.2 Kubelet
print_section "4.2 Kubelet"

# 4.2.1 Ensure that the --anonymous-auth argument is set to false
print_check "4.2.1" "Ensure that the --anonymous-auth argument is set to false"
kubelet_args=$(ps -ef | grep "$kubeletbin" | grep -v grep || true)
kubelet_config_content=""
if test -e "$kubeletconf"; then
    kubelet_config_content=$(cat "$kubeletconf" 2>/dev/null || echo "")
fi

anonymous_auth_found=false
if echo "$kubelet_args" | grep -q -- "--anonymous-auth=false"; then
    echo "PASS: --anonymous-auth=false found in kubelet arguments"
    anonymous_auth_found=true
elif echo "$kubelet_config_content" | grep -q "authentication:" && echo "$kubelet_config_content" | grep -A 5 "authentication:" | grep -q "anonymous:" && echo "$kubelet_config_content" | grep -A 5 "anonymous:" | grep -q "enabled: false"; then
    echo "PASS: authentication.anonymous.enabled: false found in kubelet config"
    anonymous_auth_found=true
elif echo "$kubelet_config_content" | grep -q "authentication:" && echo "$kubelet_config_content" | grep -A 5 "authentication:" | grep -q "anonymous:" && ! echo "$kubelet_config_content" | grep -A 5 "anonymous:" | grep -q "enabled:"; then
    echo "PASS: authentication.anonymous.enabled not set in kubelet config (defaults to false)"
    anonymous_auth_found=true
else
    echo "FAIL: --anonymous-auth is not set to false"
fi
print_remediation "If using a Kubelet config file, edit the file to set \`authentication: anonymous: enabled\` to
\`false\`.
If using executable arguments, edit the kubelet service file
$kubeletsvc on each worker node and
set the below parameter in KUBELET_SYSTEM_PODS_ARGS variable.
\`--anonymous-auth=false\`
Based on your system, restart the kubelet service. For example,
systemctl daemon-reload
systemctl restart kubelet.service"

# 4.2.2 Ensure that the --authorization-mode argument is not set to AlwaysAllow
print_check "4.2.2" "Ensure that the --authorization-mode argument is not set to AlwaysAllow"
auth_mode_found=false
if echo "$kubelet_args" | grep -q -- "--authorization-mode" && ! echo "$kubelet_args" | grep -q -- "--authorization-mode=AlwaysAllow"; then
    echo "PASS: --authorization-mode is not set to AlwaysAllow in kubelet arguments"
    auth_mode_found=true
elif echo "$kubelet_config_content" | grep -q "authorization:" && echo "$kubelet_config_content" | grep -A 5 "authorization:" | grep -q "mode:" && ! echo "$kubelet_config_content" | grep -A 5 "authorization:" | grep -q "mode: AlwaysAllow"; then
    echo "PASS: authorization.mode is not set to AlwaysAllow in kubelet config"
    auth_mode_found=true
else
    echo "FAIL: --authorization-mode is set to AlwaysAllow or not properly configured"
fi
print_remediation "If using a Kubelet config file, edit the file to set \`authorization.mode\` to Webhook. If
using executable arguments, edit the kubelet service file
$kubeletsvc on each worker node and
set the below parameter in KUBELET_AUTHZ_ARGS variable.
--authorization-mode=Webhook
Based on your system, restart the kubelet service. For example,
systemctl daemon-reload
systemctl restart kubelet.service"

# 4.2.3 Ensure that the --client-ca-file argument is set as appropriate
print_check "4.2.3" "Ensure that the --client-ca-file argument is set as appropriate"
client_ca_found=false
if echo "$kubelet_args" | grep -q -- "--client-ca-file="; then
    echo "PASS: --client-ca-file argument is set in kubelet arguments"
    client_ca_found=true
elif echo "$kubelet_config_content" | grep -q "authentication:" && echo "$kubelet_config_content" | grep -A 10 "authentication:" | grep -q "x509:" && echo "$kubelet_config_content" | grep -A 10 "authentication:" | grep -A 5 "x509:" | grep -q "clientCAFile:"; then
    echo "PASS: authentication.x509.clientCAFile is set in kubelet config"
    client_ca_found=true
else
    echo "FAIL: --client-ca-file argument is not set"
fi
print_remediation "If using a Kubelet config file, edit the file to set \`authentication.x509.clientCAFile\` to
the location of the client CA file.
If using command line arguments, edit the kubelet service file
$kubeletsvc on each worker node and
set the below parameter in KUBELET_AUTHZ_ARGS variable.
--client-ca-file=<path/to/client-ca-file>
Based on your system, restart the kubelet service. For example,
systemctl daemon-reload
systemctl restart kubelet.service"

# 4.2.4 Verify that the --read-only-port argument is set to 0
print_check "4.2.4" "Verify that the --read-only-port argument is set to 0"
readonly_port_found=false
if echo "$kubelet_args" | grep -q -- "--read-only-port=0"; then
    echo "PASS: --read-only-port=0 found in kubelet arguments"
    readonly_port_found=true
elif echo "$kubelet_config_content" | grep -q "readOnlyPort:" && echo "$kubelet_config_content" | grep "readOnlyPort:" | grep -q "0"; then
    echo "PASS: readOnlyPort: 0 found in kubelet config"
    readonly_port_found=true
elif echo "$kubelet_config_content" | grep -q "readOnlyPort:" && ! echo "$kubelet_config_content" | grep "readOnlyPort:" | grep -q "[0-9]"; then
    echo "PASS: readOnlyPort not set in kubelet config (defaults to 0)"
    readonly_port_found=true
else
    echo "FAIL: --read-only-port is not set to 0"
fi
print_remediation "If using a Kubelet config file, edit the file to set \`readOnlyPort\` to 0.
If using command line arguments, edit the kubelet service file
$kubeletsvc on each worker node and
set the below parameter in KUBELET_SYSTEM_PODS_ARGS variable.
--read-only-port=0
Based on your system, restart the kubelet service. For example,
systemctl daemon-reload
systemctl restart kubelet.service"

# 4.2.5 Ensure that the --streaming-connection-idle-timeout argument is not set to 0
print_check "4.2.5" "Ensure that the --streaming-connection-idle-timeout argument is not set to 0"
streaming_timeout_found=false
if echo "$kubelet_args" | grep -q -- "--streaming-connection-idle-timeout" && ! echo "$kubelet_args" | grep -q -- "--streaming-connection-idle-timeout=0"; then
    echo "PASS: --streaming-connection-idle-timeout is not set to 0 in kubelet arguments"
    streaming_timeout_found=true
elif echo "$kubelet_config_content" | grep -q "streamingConnectionIdleTimeout:" && ! echo "$kubelet_config_content" | grep "streamingConnectionIdleTimeout:" | grep -q "0"; then
    echo "PASS: streamingConnectionIdleTimeout is not set to 0 in kubelet config"
    streaming_timeout_found=true
elif echo "$kubelet_config_content" | grep -q "streamingConnectionIdleTimeout:" && ! echo "$kubelet_config_content" | grep "streamingConnectionIdleTimeout:" | grep -q "[0-9]"; then
    echo "PASS: streamingConnectionIdleTimeout not set in kubelet config (uses default value)"
    streaming_timeout_found=true
else
    echo "FAIL: --streaming-connection-idle-timeout is set to 0 or not properly configured"
fi
print_remediation "If using a Kubelet config file, edit the file to set \`streamingConnectionIdleTimeout\` to a
value other than 0.
If using command line arguments, edit the kubelet service file
$kubeletsvc on each worker node and
set the below parameter in KUBELET_SYSTEM_PODS_ARGS variable.
--streaming-connection-idle-timeout=5m
Based on your system, restart the kubelet service. For example,
systemctl daemon-reload
systemctl restart kubelet.service"

# 4.2.6 Ensure that the --make-iptables-util-chains argument is set to true
print_check "4.2.6" "Ensure that the --make-iptables-util-chains argument is set to true"
iptables_chains_found=false
if echo "$kubelet_args" | grep -q -- "--make-iptables-util-chains=true"; then
    echo "PASS: --make-iptables-util-chains=true found in kubelet arguments"
    iptables_chains_found=true
elif echo "$kubelet_config_content" | grep -q "makeIPTablesUtilChains:" && echo "$kubelet_config_content" | grep "makeIPTablesUtilChains:" | grep -q "true"; then
    echo "PASS: makeIPTablesUtilChains: true found in kubelet config"
    iptables_chains_found=true
elif echo "$kubelet_config_content" | grep -q "makeIPTablesUtilChains:" && ! echo "$kubelet_config_content" | grep "makeIPTablesUtilChains:" | grep -q "[a-zA-Z]"; then
    echo "PASS: makeIPTablesUtilChains not set in kubelet config (defaults to true)"
    iptables_chains_found=true
else
    echo "FAIL: --make-iptables-util-chains is not set to true"
fi
print_remediation "If using a Kubelet config file, edit the file to set \`makeIPTablesUtilChains\` to \`true\`.
If using command line arguments, edit the kubelet service file
$kubeletsvc on each worker node and
remove the --make-iptables-util-chains argument from the
KUBELET_SYSTEM_PODS_ARGS variable.
Based on your system, restart the kubelet service. For example:
systemctl daemon-reload
systemctl restart kubelet.service"

# 4.2.7 Ensure that the --hostname-override argument is not set
print_check "4.2.7" "Ensure that the --hostname-override argument is not set"
hostname_override_found=false
if ! echo "$kubelet_args" | grep -q -- "--hostname-override"; then
    echo "PASS: --hostname-override argument is not set in kubelet arguments"
    hostname_override_found=true
else
    echo "FAIL: --hostname-override argument is set in kubelet arguments"
fi
print_remediation "Edit the kubelet service file $kubeletsvc
on each worker node and remove the --hostname-override argument from the
KUBELET_SYSTEM_PODS_ARGS variable.
Based on your system, restart the kubelet service. For example,
systemctl daemon-reload
systemctl restart kubelet.service"

# 4.2.10 Ensure that the --rotate-certificates argument is not set to false
print_check "4.2.10" "Ensure that the --rotate-certificates argument is not set to false"
rotate_certs_found=false
if echo "$kubelet_args" | grep -q -- "--rotate-certificates=true"; then
    echo "PASS: --rotate-certificates=true found in kubelet arguments"
    rotate_certs_found=true
elif echo "$kubelet_config_content" | grep -q "rotateCertificates:" && echo "$kubelet_config_content" | grep "rotateCertificates:" | grep -q "true"; then
    echo "PASS: rotateCertificates: true found in kubelet config"
    rotate_certs_found=true
elif echo "$kubelet_config_content" | grep -q "rotateCertificates:" && ! echo "$kubelet_config_content" | grep "rotateCertificates:" | grep -q "[a-zA-Z]"; then
    echo "PASS: rotateCertificates not set in kubelet config (defaults to true)"
    rotate_certs_found=true
else
    echo "FAIL: --rotate-certificates is set to false or not properly configured"
fi
print_remediation "If using a Kubelet config file, edit the file to add the line \`rotateCertificates\` to \`true\` or
remove it altogether to use the default value.
If using command line arguments, edit the kubelet service file
$kubeletsvc on each worker node and
remove --rotate-certificates=false argument from the KUBELET_CERTIFICATE_ARGS
variable.
Based on your system, restart the kubelet service. For example,
systemctl daemon-reload
systemctl restart kubelet.service"

# 4.3 kube-proxy
print_section "4.3 kube-proxy"

# 4.3.1 Ensure that the kube-proxy metrics service is bound to localhost
print_check "4.3.1" "Ensure that the kube-proxy metrics service is bound to localhost"
proxy_args=$(ps -ef | grep "$proxybin" | grep -v grep || true)
proxy_config_content=""
if test -e "$proxykubeconfig"; then
    proxy_config_content=$(cat "$proxykubeconfig" 2>/dev/null || echo "")
fi

metrics_bind_found=false
if echo "$proxy_args" | grep -q -- "--metrics-bind-address" && echo "$proxy_args" | grep -q -- "--metrics-bind-address=127.0.0.1"; then
    echo "PASS: --metrics-bind-address=127.0.0.1 found in kube-proxy arguments"
    metrics_bind_found=true
elif echo "$proxy_config_content" | grep -q "metricsBindAddress:" && echo "$proxy_config_content" | grep "metricsBindAddress:" | grep -q "127.0.0.1"; then
    echo "PASS: metricsBindAddress: 127.0.0.1 found in kube-proxy config"
    metrics_bind_found=true
elif echo "$proxy_config_content" | grep -q "metricsBindAddress:" && ! echo "$proxy_config_content" | grep "metricsBindAddress:" | grep -q "[0-9]"; then
    echo "PASS: metricsBindAddress not set in kube-proxy config (uses default localhost)"
    metrics_bind_found=true
else
    echo "FAIL: kube-proxy metrics service is not bound to localhost"
fi
print_remediation "Modify or remove any values which bind the metrics service to a non-localhost address.
The default value is 127.0.0.1:10249."

echo ""
echo "========================================================================="
echo "CIS checks completed. Please review the output above for any FAIL results."
echo "For failed checks, see the remediation steps provided."
echo "Note: This script implements a subset of checks from the CIS benchmark."
echo "For a complete assessment, use kube-bench or a similar tool."