#!groovy

def tag_image_as(imageUrl, tag) {
  script {
    docker.image("${imageUrl}:${env.BUILD_NUMBER}").push(tag)
    sh "docker rmi ${imageUrl}:${tag} || true"
  }
}

def deploy(app, environment) {
  build job: 'Subtask_Openstack_Playbook',
    parameters: [
        [$class: 'StringParameterValue', name: 'INVENTORY', value: environment],
        [$class: 'StringParameterValue', name: 'PLAYBOOK', value: 'deploy.yml'],
        [$class: 'StringParameterValue', name: 'PLAYBOOKPARAMS', value: "-e cmdb_id=app_${app}"],
    ]
}

pipeline {

  agent any

  environment {
    GROUP = "vnor"
    BACKEND_APP = "bereikbaarheid-backend"
    BACKEND_DOCKERFILE = "Dockerfile"
    BACKEND_DOCKER_BUILD_CONTEXT = "."
    BACKEND_DOCKER_IMAGE = "${GROUP}/${BACKEND_APP}"
    BACKEND_DOCKER_IMAGE_URL = "${DOCKER_REGISTRY_NO_PROTOCOL}/${BACKEND_DOCKER_IMAGE}"
  }

  stages {

    stage("Checkout") {
      steps {
        checkout scm
        script { env.COMMIT_HASH = sh(returnStdout: true, script: "git log -n 1 --pretty=format:'%h'").trim() }
      }
    }

    stage("Build docker image") {
      steps {
        script {
          def backend_image = docker.build("${BACKEND_DOCKER_IMAGE_URL}:${env.BUILD_NUMBER}","-f ${BACKEND_DOCKERFILE} ${BACKEND_DOCKER_BUILD_CONTEXT}")
          backend_image.push()
        }
      }
    }

    stage("Push and deploy acceptance image") {
      when { branch 'main' }
      steps {
        tag_image_as("${BACKEND_DOCKER_IMAGE_URL}", "acceptance")
        deploy("${BACKEND_APP}", "acceptance")
      }
    }

    stage("Deploy to production") {
      when { branch 'main' }
      options {
        timeout(time: 6, unit: 'HOURS')
      }
      input {
        message "Deploy to Production?"
        ok "Yes, deploy it!"
      }
      steps {
        tag_image_as("${BACKEND_DOCKER_IMAGE_URL}", "latest")
        tag_image_as("${BACKEND_DOCKER_IMAGE_URL}", "production")
        deploy("${BACKEND_APP}", "production")
      }
    }

  }

  post {
    always {
      script { sh "docker rmi ${BACKEND_DOCKER_IMAGE_URL}:${env.BUILD_NUMBER} || true" }
    }
  }

}
