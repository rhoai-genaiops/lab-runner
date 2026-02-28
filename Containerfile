FROM registry.access.redhat.com/ubi9/python-311

# Install oc + helm CLI tools (git is already in the base image)
RUN curl -sL https://mirror.openshift.com/pub/openshift-v4/clients/ocp/stable/openshift-client-linux.tar.gz \
    | tar xzf - -C /usr/local/bin oc kubectl && \
    curl -sL https://get.helm.sh/helm-v3.17.3-linux-amd64.tar.gz \
    | tar xzf - --strip-components=1 -C /usr/local/bin linux-amd64/helm && \
    chmod +x /usr/local/bin/oc /usr/local/bin/kubectl /usr/local/bin/helm

WORKDIR /opt/app-root/src
COPY . .
RUN pip install --no-cache-dir .

EXPOSE 8080
USER 1001
CMD ["uvicorn", "lab_runner.web:app", "--host", "0.0.0.0", "--port", "8080"]
