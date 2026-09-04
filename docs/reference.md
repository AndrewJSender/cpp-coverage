# References

## CI

[Code Coverage Example CI](https://psplatform.ci.corp.adobe.com/job/Phoenix/job/code_coverage_example/) is based around the code coverage example in this repo.

### Jenkins

Start with the [psplatform.ci](https://psplatform.ci.corp.adobe.com/) jenkins instance for the available mac resources.

Slack Channels

- CI
- Support

### Artifactory

Create the [generic-code-coverage-release](https://artifactory.corp.adobe.com/ui/native/generic-code-coverage-release) an artifactory repo from [Adobe's devhome](https://devhome.corp.adobe.com/artifacts/repositories)

### Web Server

http://sj1010010244149.corp.adobe.com/website/

#### ATS

Create an ubuntu virtual machine (vm) from [ATS](https://atscloud.corp.adobe.com/#/compute/virtual-compute).

- Enable ports 80 and others to allow HTTP/S traffic to the vm.

#### Apache2

The web server uses apache2 to run the http daemon (httpd). [Follow these steps from ubuntu website](https://ubuntu.com/tutorials/install-and-configure-apache#1-overview)

Note: make sure all folders have `chmod +x` permissions.

For `/etc/apache2/sites-available/gci.con` file

```
ServerName sj1010010244149.corp.adobe.com
ServerAdmin sender@adobe.com
DocumentRoot "/jenkins/code_coverage/gitws-0"
<Directory "/jenkins/code_coverage/gitws-0">
        Options Indexes FollowSymLinks
        Require all granted
</Directory>
```

## DVA Coverage Tool

https://git.corp.adobe.com/AdobeShared/coverage
