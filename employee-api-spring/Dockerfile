FROM maven:3.9.9-eclipse-temurin-17 AS build
WORKDIR /build
COPY employee-api-spring/pom.xml .
RUN mkdir -p /root/.m2 && printf '%s' '<settings><mirrors><mirror><id>google-central</id><mirrorOf>central</mirrorOf><url>https://maven-central.storage-download.googleapis.com/maven2/</url></mirror></mirrors></settings>' > /root/.m2/settings.xml
COPY employee-api-spring/src src
RUN mvn -q -DskipTests package

FROM eclipse-temurin:17-jre-jammy
WORKDIR /app
COPY --from=build /build/target/employee-api-1.0.0.jar app.jar
EXPOSE 8080
ENTRYPOINT ["java", "-jar", "app.jar"]
