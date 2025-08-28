#!/bin/bash

# This script performs manual checks based on CIS Kubernetes Benchmark v1.9 policies.yml
# Note: Automated checks require integration with kube-bench or similar tools for full compliance testing.

set -e

echo "Running CIS Kubernetes Benchmark v1.9 checks from policies.yml..."

# === 5.1 RBAC and Service Accounts ===
echo -e "\n=== 5.1 RBAC and Service Accounts ==="

# 5.1.1 Ensure that the cluster-admin role is only used where required (Automated)
# Note: This is an automated check in kube-bench. This script provides a manual check.
echo "5.1.1 Ensure that the cluster-admin role is only used where required:"
echo "Manual Check: Review clusterrolebindings for cluster-admin role usage."
kubectl get clusterrolebindings -o=custom-columns=NAME:.metadata.name,ROLE:.roleRef.name,SUBJECT:.subjects[*].name --no-headers | while read -r role_name role_binding subject; do
  if [[ "${role_name}" != "cluster-admin" && "${role_binding}" == "cluster-admin" ]]; then
    echo "  WARNING: Found clusterrolebinding with cluster-admin role but not named cluster-admin: ${role_name}"
  fi
done
echo "Remediation: Identify all clusterrolebindings to the cluster-admin role. Check if they are used and
if they need this role or if they could use a role with fewer privileges.
Where possible, first bind users to a lower privileged role and then remove the
clusterrolebinding to the cluster-admin role : kubectl delete clusterrolebinding [name]"
echo ""

# 5.1.2 Minimize access to secrets (Automated)
# Note: This is an automated check in kube-bench.
# WARNING: The kubectl command below can hang or take a very long time in large clusters.
# This script uses a timeout mechanism as a workaround.
echo "5.1.2 Minimize access to secrets:"
# Use a timeout to prevent the script from hanging indefinitely.
# Adjust the timeout duration (in seconds) as needed for your environment.
timeout_duration=30
if command -v timeout &> /dev/null; then
    access_secrets=$(timeout "${timeout_duration}" kubectl auth can-i get,list,watch secrets --all-namespaces --as=system:authenticated 2>&1)
    exit_status=$?
    if [ $exit_status -eq 124 ]; then
        echo "  WARNING: Command timed out after ${timeout_duration} seconds. This might indicate a problem or a large number of namespaces."
        echo "  Manual Check Required: Please manually verify access to secrets for system:authenticated."
    else
        echo "  system:authenticated can get/list/watch secrets: ${access_secrets}"
        if [[ "${access_secrets}" == "yes" ]]; then
          echo "  WARNING: system:authenticated has access to secrets."
        fi
    fi
else
    # Fallback for systems without the 'timeout' command (like macOS)
    # Start the command in the background and kill it after the timeout
    echo "  Checking access (this might take a moment or timeout)..."
    kubectl auth can-i get,list,watch secrets --all-namespaces --as=system:authenticated > /tmp/kubectl_secrets_check.out 2>&1 &
    bg_pid=$!
    (
        sleep "${timeout_duration}"
        if kill -0 $bg_pid 2>/dev/null; then
            echo "  WARNING: Command timed out after ${timeout_duration} seconds. Killing the process."
            kill $bg_pid 2>/dev/null
            echo "  WARNING: Command timed out. This might indicate a problem or a large number of namespaces."
            echo "  Manual Check Required: Please manually verify access to secrets for system:authenticated."
            # Clear the output file if it was created
            > /tmp/kubectl_secrets_check.out
        fi
    ) &
    killer_pid=$!
    wait $bg_pid 2>/dev/null
    wait_status=$?
    kill $killer_pid 2>/dev/null
    # Read the output if the command completed before the timeout
    if [ -s /tmp/kubectl_secrets_check.out ]; then
        access_secrets=$(cat /tmp/kubectl_secrets_check.out)
        echo "  system:authenticated can get/list/watch secrets: ${access_secrets}"
        if [[ "${access_secrets}" == "yes" ]]; then
          echo "  WARNING: system:authenticated has access to secrets."
        fi
        rm -f /tmp/kubectl_secrets_check.out
    fi
fi
echo "Remediation: Where possible, remove get, list and watch access to Secret objects in the cluster."
echo ""

# 5.1.3 Minimize wildcard use in Roles and ClusterRoles (Automated)
# Note: This is an automated check in kube-bench. This script provides a manual check.
echo "5.1.3 Minimize wildcard use in Roles and ClusterRoles:"
found_wildcard_role=false
found_wildcard_clusterrole=false

# Check Roles
kubectl get roles --all-namespaces -o custom-columns=ROLE_NAMESPACE:.metadata.namespace,ROLE_NAME:.metadata.name --no-headers | while read -r role_namespace role_name; do
  if [[ -n "${role_namespace}" && -n "${role_name}" ]]; then
    role_rules=$(kubectl get role -n "${role_namespace}" "${role_name}" -o=json | jq -c '.rules' 2>/dev/null || echo "[]")
    if echo "${role_rules}" | grep -q '\["*"\]'; then
      echo "  WARNING: Role ${role_name} in namespace ${role_namespace} uses wildcard [*] in rules."
      found_wildcard_role=true
    fi
  fi
done

# Check ClusterRoles
kubectl get clusterroles -o custom-columns=CLUSTERROLE_NAME:.metadata.name --no-headers | while read -r clusterrole_name; do
  if [[ -n "${clusterrole_name}" ]]; then
    clusterrole_rules=$(kubectl get clusterrole "${clusterrole_name}" -o=json | jq -c '.rules' 2>/dev/null || echo "[]")
    if echo "${clusterrole_rules}" | grep -q '\["*"\]'; then
      echo "  WARNING: ClusterRole ${clusterrole_name} uses wildcard [*] in rules."
      found_wildcard_clusterrole=true
    fi
  fi
done

if [[ "${found_wildcard_role}" == false && "${found_wildcard_clusterrole}" == false ]]; then
  echo "  No wildcards [*] found in Roles or ClusterRoles."
fi
echo "Remediation: Where possible replace any use of wildcards [\"*\"] in roles and clusterroles with specific
objects or actions."
echo ""

# 5.1.4 Minimize access to create pods (Automated)
# Note: This is an automated check in kube-bench.
echo "5.1.4 Minimize access to create pods:"
can_create_pods=$(kubectl auth can-i create pods --all-namespaces --as=system:authenticated 2>&1)
echo "  system:authenticated can create pods: ${can_create_pods}"
if [[ "${can_create_pods}" == "yes" ]]; then
  echo "  WARNING: system:authenticated can create pods."
fi
echo "Remediation: Where possible, remove create access to pod objects in the cluster."
echo ""

# 5.1.5 Ensure that default service accounts are not actively used (Automated)
# Note: This is an automated check in kube-bench.
echo "5.1.5 Ensure that default service accounts are not actively used:"
default_sas=$(kubectl get serviceaccount --all-namespaces --field-selector metadata.name=default -o=json | jq -r '.items[] | "namespace: \(.metadata.namespace), automountServiceAccountToken: \(.automountServiceAccountToken // "notset")"' 2>/dev/null || echo "")
if [[ -n "${default_sas}" ]]; then
  echo "${default_sas}" | while IFS= read -r line; do
    namespace=$(echo "${line}" | cut -d' ' -f2 | tr -d ',')
    automount_token=$(echo "${line}" | cut -d' ' -f4)
    if [[ "${automount_token}" == "true" || "${automount_token}" == "notset" ]]; then
      echo "  WARNING: Default service account in namespace ${namespace} has automountServiceAccountToken: ${automount_token}"
    fi
  done
else
  echo "  No default service accounts found or error retrieving them."
fi
echo "Remediation: Create explicit service accounts wherever a Kubernetes workload requires specific access
to the Kubernetes API server.
Modify the configuration of each default service account to include this value
\`automountServiceAccountToken: false\`."
echo ""

# 5.1.6 Ensure that Service Account Tokens are only mounted where necessary (Automated)
# Note: This is an automated check in kube-bench.
echo "5.1.6 Ensure that Service Account Tokens are only mounted where necessary:"
non_compliant_pods=false
kubectl get pods --all-namespaces -o custom-columns=POD_NAMESPACE:.metadata.namespace,POD_NAME:.metadata.name,POD_SERVICE_ACCOUNT:.spec.serviceAccount,POD_IS_AUTOMOUNTSERVICEACCOUNTTOKEN:.spec.automountServiceAccountToken --no-headers | while read -r pod_namespace pod_name pod_service_account pod_is_automountserviceaccounttoken; do
  # Retrieve automountServiceAccountToken's value for ServiceAccount and Pod, set to notset if null or <none>.
  svacc_is_automountserviceaccounttoken=$(kubectl get serviceaccount -n "${pod_namespace}" "${pod_service_account}" -o json | jq -r '.automountServiceAccountToken' 2>/dev/null | sed -e 's/<none>/notset/g' -e 's/null/notset/g' || echo "notset")
  pod_is_automountserviceaccounttoken=$(echo "${pod_is_automountserviceaccounttoken}" | sed -e 's/<none>/notset/g' -e 's/null/notset/g')

  is_compliant="true"
  if [ "${svacc_is_automountserviceaccounttoken}" = "false" ] && ( [ "${pod_is_automountserviceaccounttoken}" = "false" ] || [ "${pod_is_automountserviceaccounttoken}" = "notset" ] ); then
    is_compliant="true"
  elif [ "${svacc_is_automountserviceaccounttoken}" = "true" ] && [ "${pod_is_automountserviceaccounttoken}" = "false" ]; then
    is_compliant="true"
  else
    is_compliant="false"
  fi

  if [ "${is_compliant}" = "false" ]; then
    echo "  WARNING: Pod ${pod_name} in namespace ${pod_namespace} (ServiceAccount: ${pod_service_account}) is not compliant."
    echo "    ServiceAccount automountServiceAccountToken: ${svacc_is_automountserviceaccounttoken}"
    echo "    Pod automountServiceAccountToken: ${pod_is_automountserviceaccounttoken}"
    non_compliant_pods=true
  fi
done

if [[ "${non_compliant_pods}" == false ]]; then
  echo "  All checked pods are compliant with service account token mounting policies."
fi
echo "Remediation: Modify the definition of ServiceAccounts and Pods which do not need to mount service
account tokens to disable it, with \`automountServiceAccountToken: false\`.
If both the ServiceAccount and the Pod's .spec specify a value for automountServiceAccountToken, the Pod spec takes precedence."
echo ""

# Manual Checks (5.1.7 - 5.1.13)
echo "5.1.7 Avoid use of system:masters group (Manual)"
echo "  Manual Check: Review all users and groups in the cluster for system:masters usage."
echo "  Remediation: Remove the system:masters group from all users in the cluster."
echo ""

echo "5.1.8 Limit use of the Bind, Impersonate and Escalate permissions in the Kubernetes cluster (Manual)"
echo "  Manual Check: Review roles and clusterroles for these permissions."
echo "  Remediation: Where possible, remove the impersonate, bind and escalate rights from subjects."
echo ""

echo "5.1.9 Minimize access to create persistent volumes (Manual)"
echo "  Manual Check: Review who can create PersistentVolumes."
echo "  Remediation: Where possible, remove create access to PersistentVolume objects in the cluster."
echo ""

echo "5.1.10 Minimize access to the proxy sub-resource of nodes (Manual)"
echo "  Manual Check: Review access to node proxy sub-resources."
echo "  Remediation: Where possible, remove access to the proxy sub-resource of node objects."
echo ""

echo "5.1.11 Minimize access to the approval sub-resource of certificatesigningrequests objects (Manual)"
echo "  Manual Check: Review access to CSR approval sub-resources."
echo "  Remediation: Where possible, remove access to the approval sub-resource of certificatesigningrequest objects."
echo ""

echo "5.1.12 Minimize access to webhook configuration objects (Manual)"
echo "  Manual Check: Review access to validating/mutating webhook configurations."
echo "  Remediation: Where possible, remove access to the validatingwebhookconfigurations or mutatingwebhookconfigurations objects"
echo ""

echo "5.1.13 Minimize access to the service account token creation (Manual)"
echo "  Manual Check: Review access to service account token sub-resources."
echo "  Remediation: Where possible, remove access to the token sub-resource of serviceaccount objects."
echo ""

# === 5.2 Pod Security Standards ===
echo -e "\n=== 5.2 Pod Security Standards ==="

# Manual Checks (5.2.1 - 5.2.13)
echo "5.2.1 Ensure that the cluster has at least one active policy control mechanism in place (Manual)"
echo "  Manual Check: Verify if Pod Security Admission or an external policy control system is in place for every namespace with user workloads."
echo "  Remediation: Ensure that either Pod Security Admission or an external policy control system is in place
for every namespace which contains user workloads."
echo ""

echo "5.2.2 Minimize the admission of privileged containers (Manual)"
echo "  Manual Check: Review policies for privileged container admission."
echo "  Remediation: Add policies to each namespace in the cluster which has user workloads to restrict the
admission of privileged containers."
echo ""

echo "5.2.3 Minimize the admission of containers wishing to share the host process ID namespace (Manual)"
echo "  Manual Check: Review policies for hostPID containers."
echo "  Remediation: Add policies to each namespace in the cluster which has user workloads to restrict the
admission of \`hostPID\` containers."
echo ""

echo "5.2.4 Minimize the admission of containers wishing to share the host IPC namespace (Manual)"
echo "  Manual Check: Review policies for hostIPC containers."
echo "  Remediation: Add policies to each namespace in the cluster which has user workloads to restrict the
admission of \`hostIPC\` containers."
echo ""

echo "5.2.5 Minimize the admission of containers wishing to share the host network namespace (Manual)"
echo "  Manual Check: Review policies for hostNetwork containers."
echo "  Remediation: Add policies to each namespace in the cluster which has user workloads to restrict the
admission of \`hostNetwork\` containers."
echo ""

echo "5.2.6 Minimize the admission of containers with allowPrivilegeEscalation (Manual)"
echo "  Manual Check: Review policies for allowPrivilegeEscalation."
echo "  Remediation: Add policies to each namespace in the cluster which has user workloads to restrict the
admission of containers with \`.spec.allowPrivilegeEscalation\` set to \`true\`."
echo ""

echo "5.2.7 Minimize the admission of root containers (Manual)"
echo "  Manual Check: Review policies for root user containers."
echo "  Remediation: Create a policy for each namespace in the cluster, ensuring that either \`MustRunAsNonRoot\`
or \`MustRunAs\` with the range of UIDs not including 0, is set."
echo ""

echo "5.2.8 Minimize the admission of containers with the NET_RAW capability (Manual)"
echo "  Manual Check: Review policies for NET_RAW capability."
echo "  Remediation: Add policies to each namespace in the cluster which has user workloads to restrict the
admission of containers with the \`NET_RAW\` capability."
echo ""

echo "5.2.9 Minimize the admission of containers with added capabilities (Manual)"
echo "  Manual Check: Review policies for allowedCapabilities."
echo "  Remediation: Ensure that \`allowedCapabilities\` is not present in policies for the cluster unless
it is set to an empty array."
echo ""

echo "5.2.10 Minimize the admission of containers with capabilities assigned (Manual)"
echo "  Manual Check: Review use of capabilities in applications and policies."
echo "  Remediation: Review the use of capabilites in applications running on your cluster. Where a namespace
contains applications which do not require any Linux capabities to operate consider adding
a PSP which forbids the admission of containers which do not drop all capabilities."
echo ""

echo "5.2.11 Minimize the admission of Windows HostProcess containers (Manual)"
echo "  Manual Check: Review policies for Windows HostProcess containers."
echo "  Remediation: Add policies to each namespace in the cluster which has user workloads to restrict the
admission of containers that have \`.securityContext.windowsOptions.hostProcess\` set to \`true\`."
echo ""

echo "5.2.12 Minimize the admission of HostPath volumes (Manual)"
echo "  Manual Check: Review policies for HostPath volumes."
echo "  Remediation: Add policies to each namespace in the cluster which has user workloads to restrict the
admission of containers with \`hostPath\` volumes."
echo ""

echo "5.2.13 Minimize the admission of containers which use HostPorts (Manual)"
echo "  Manual Check: Review policies for HostPort usage."
echo "  Remediation: Add policies to each namespace in the cluster which has user workloads to restrict the
admission of containers which use \`hostPort\` sections."
echo ""

# === 5.3 Network Policies and CNI ===
echo -e "\n=== 5.3 Network Policies and CNI ==="

# Manual Checks (5.3.1 - 5.3.2)
echo "5.3.1 Ensure that the CNI in use supports NetworkPolicies (Manual)"
echo "  Manual Check: Verify that your CNI plugin supports Network Policies."
echo "  Remediation: If the CNI plugin in use does not support network policies, consideration should be given to
making use of a different plugin, or finding an alternate mechanism for restricting traffic
in the Kubernetes cluster."
echo ""

echo "5.3.2 Ensure that all Namespaces have NetworkPolicies defined (Manual)"
echo "  Manual Check: Verify that all namespaces have NetworkPolicies."
echo "  Remediation: Follow the documentation and create NetworkPolicy objects as you need them."
echo ""

# === 5.4 Secrets Management ===
echo -e "\n=== 5.4 Secrets Management ==="

# Manual Checks (5.4.1 - 5.4.2)
echo "5.4.1 Prefer using Secrets as files over Secrets as environment variables (Manual)"
echo "  Manual Check: Review application code for secret usage."
echo "  Remediation: If possible, rewrite application code to read Secrets from mounted secret files, rather than
from environment variables."
echo ""

echo "5.4.2 Consider external secret storage (Manual)"
echo "  Manual Check: Evaluate external secret storage solutions."
echo "  Remediation: Refer to the Secrets management options offered by your cloud provider or a third-party
secrets management solution."
echo ""

# === 5.5 Extensible Admission Control ===
echo -e "\n=== 5.5 Extensible Admission Control ==="

# Manual Check (5.5.1)
echo "5.5.1 Configure Image Provenance using ImagePolicyWebhook admission controller (Manual)"
echo "  Manual Check: Verify if ImagePolicyWebhook is configured."
echo "  Remediation: Follow the Kubernetes documentation and setup image provenance."
echo ""

# === 5.7 General Policies ===
echo -e "\n=== 5.7 General Policies ==="

# Manual Checks (5.7.1 - 5.7.4)
echo "5.7.1 Create administrative boundaries between resources using namespaces (Manual)"
echo "  Manual Check: Review namespace usage for resource segregation."
echo "  Remediation: Follow the documentation and create namespaces for objects in your deployment as you need
them."
echo ""

echo "5.7.2 Ensure that the seccomp profile is set to docker/default in your Pod definitions (Manual)"
echo "  Manual Check: Review pod definitions for seccomp profiles."
echo "  Remediation: Use \`securityContext\` to enable the docker/default seccomp profile in your pod definitions.
An example is as below:
  securityContext:
    seccompProfile:
      type: RuntimeDefault"
echo ""

echo "5.7.3 Apply SecurityContext to your Pods and Containers (Manual)"
echo "  Manual Check: Review pod and container definitions for SecurityContext."
echo "  Remediation: Follow the Kubernetes documentation and apply SecurityContexts to your Pods. For a
suggested list of SecurityContexts, you may refer to the CIS Security Benchmark for Docker
Containers."
echo ""

echo "5.7.4 The default namespace should not be used (Manual)"
echo "  Manual Check: Verify that the default namespace is not being used for workloads."
echo "  Remediation: Ensure that namespaces are created to allow for appropriate segregation of Kubernetes
resources and that all new resources are created in a specific namespace."
echo ""

echo -e "\n=== CIS Check Summary ==="
echo "This script has performed manual checks for CIS Kubernetes Benchmark v1.9 policies.yml."
echo "Some checks (5.1.1, 5.1.3, 5.1.5, 5.1.6) have basic automated checks implemented."
echo "For full compliance testing with automated checks, please use kube-bench or a similar tool."
echo "Review the output above for warnings and recommended remediation steps."