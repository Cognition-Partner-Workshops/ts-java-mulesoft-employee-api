package com.example.employee;

import java.util.List;
import java.util.Map;
import org.postgresql.ds.PGSimpleDataSource;
import org.springframework.core.io.ClassPathResource;
import org.springframework.jdbc.core.namedparam.NamedParameterJdbcTemplate;
import org.springframework.stereotype.Component;
import com.fasterxml.jackson.core.type.TypeReference;
import com.fasterxml.jackson.databind.ObjectMapper;

@Component
public class Database {
    private final NamedParameterJdbcTemplate jdbc;
    private final Map<String, String> sql;

    public Database(ObjectMapper mapper) throws Exception {
        PGSimpleDataSource source = new PGSimpleDataSource();
        source.setURL(System.getProperty("test.db.url", System.getenv().getOrDefault("DATABASE_URL", "jdbc:postgresql://localhost:5432/employee_service")));
        source.setUser(System.getProperty("test.db.user", System.getenv().getOrDefault("DB_USER", "fixture")));
        source.setPassword(System.getProperty("test.db.password", System.getenv().getOrDefault("DB_PASSWORD", "fixture_only")));
        source.setConnectTimeout(3);
        jdbc = new NamedParameterJdbcTemplate(source);
        sql = mapper.readValue(new ClassPathResource("queries.json").getInputStream(), new TypeReference<>() {});
    }

    public List<Map<String, Object>> rows(String name, Map<String, Object> params) {
        return jdbc.queryForList(sql.get(name), params);
    }

    public int update(String name, Map<String, Object> params) {
        return jdbc.update(sql.get(name), params);
    }
}
