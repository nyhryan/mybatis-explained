# 주문 관리 예제로 배우는 MyBatis Mapper XML과 동적 SQL

Java, Spring Boot, MyBatis XML Mapper, MySQL 8.x 환경에서 주문 관리 예제를 통해 SQL 매핑과 동적 SQL을 살펴봅니다. Service는 비즈니스 검증과 트랜잭션을 담당하고, Mapper 인터페이스는 Java 메서드와 파라미터를 정의합니다. Mapper XML은 메서드에 연결되는 SQL과 결과 매핑을 정의하며, MyBatis가 JDBC를 통해 SQL을 실행합니다.

매핑 규칙과 동적 SQL 태그의 전체 목록은 MyBatis 공식 문서에서 확인할 수 있습니다. [Mapper XML Files](https://mybatis.org/mybatis-3/sqlmap-xml.html), [Dynamic SQL](https://mybatis.org/mybatis-3/dynamic-sql.html)

## 1. MyBatis의 역할과 기본 구조

Mapper를 호출하면 MyBatis가 입력값을 SQL 파라미터에 바인딩합니다. 조회 결과는 Java 객체로 매핑하고, 변경 작업은 영향 행 수를 돌려줍니다.

Mapper 인터페이스의 메서드는 XML의 `namespace`와 `id`로 SQL에 연결됩니다. Mapper XML에는 SQL 문장, 입력과 결과 매핑, 동적 SQL을 함께 정의할 수 있습니다.

## 2. 예제 DB 스키마

회원(`users`) 한 명은 여러 주문(`orders`)을 생성하고, 주문 한 건은 여러 주문 상품(`order_items`)을 가집니다. `orders.user_id`와 `order_items.order_id`가 각 관계를 연결합니다.

### 2.1 MySQL DDL

```sql
CREATE TABLE users (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    email VARCHAR(255) NOT NULL UNIQUE,
    name VARCHAR(100) NOT NULL,
    created_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB;

CREATE TABLE orders (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    user_id BIGINT NOT NULL,
    status VARCHAR(20) NOT NULL,
    total_amount DECIMAL(12, 2) NOT NULL,
    shipping_address VARCHAR(255) NOT NULL,
    memo VARCHAR(500),
    version INT NOT NULL DEFAULT 0,
    created_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP,
    updated_at DATETIME NOT NULL
        DEFAULT CURRENT_TIMESTAMP
        ON UPDATE CURRENT_TIMESTAMP,
    deleted_at DATETIME NULL,

    FOREIGN KEY (user_id) REFERENCES users(id),
    INDEX idx_orders_user_created
        (user_id, created_at)
) ENGINE=InnoDB;

CREATE TABLE order_items (
    id BIGINT PRIMARY KEY AUTO_INCREMENT,
    order_id BIGINT NOT NULL,
    product_name VARCHAR(200) NOT NULL,
    quantity INT NOT NULL,
    unit_price DECIMAL(12, 2) NOT NULL,

    FOREIGN KEY (order_id)
        REFERENCES orders(id)
        ON DELETE CASCADE,

    INDEX idx_order_items_order (order_id)
) ENGINE=InnoDB;
```

주요 컬럼의 의미는 다음과 같습니다.

- `status`: 주문 상태 (`PENDING`, `PAID`, `SHIPPED`, `CANCELLED`)
- `total_amount`: 주문 총액
- `shipping_address`: 배송 주소
- `memo`: 주문 메모
- `version`: 동시 수정 충돌을 방지하기 위한 낙관적 락 버전
- `deleted_at`: 실제 데이터를 삭제하지 않고 삭제 상태를 표시하는 소프트 삭제용 컬럼

이 예제에서는 `orders`를 실제 삭제하면 외래 키의 `ON DELETE CASCADE`에 의해 해당 `order_items`도 삭제됩니다.

## 3. CRUD별 Mapper 메서드 설계

예제에서 사용하는 메서드는 다음과 같습니다.

| 분류     | 메서드                     | 사용 목적             |
| ------ | ----------------------- | ----------------- |
| Create | `insertOrder`           | 주문 1건 생성          |
| Create | `insertItems`           | 주문 상품 여러 건 생성     |
| Read   | `findById`              | 주문 ID로 상세 정보 조회   |
| Read   | `findByCondition`       | 조건 검색과 페이징        |
| Read   | `countByCondition`      | 조건에 맞는 전체 건수 조회   |
| Read   | `existsById`            | 주문 존재 여부 확인       |
| Read   | `findByIds`             | 여러 ID로 한 번에 조회    |
| Update | `updateStatusIfVersion` | 주문 상태 변경 및 동시성 검사 |
| Update | `patchOrder`            | 전달된 필드만 부분 수정     |
| Delete | `softDeleteById`        | 논리 삭제             |
| Delete | `hardDeleteById`        | 물리 삭제             |

이 메서드를 중심으로 Mapper XML의 주요 태그를 설명합니다.

## 4. Mapper 인터페이스와 Mapper XML 연결

MyBatis는 Mapper 인터페이스의 메서드와 XML의 SQL을 이름으로 연결합니다.

예를 들어 다음과 같이 구성할 수 있습니다.

```text
src/main/java/com/example/order/
├── OrderService.java
├── OrderMapper.java
├── Order.java
├── OrderItem.java
├── OrderDetail.java
├── CustomerSummary.java
├── OrderSummary.java
├── OrderSearchCondition.java
└── OrderPatch.java

src/main/resources/
└── mappers/
    └── OrderMapper.xml
```

### 4.1 Mapper 인터페이스

```java
package com.example.order;

import java.util.List;
import org.apache.ibatis.annotations.Mapper;
import org.apache.ibatis.annotations.Param;

@Mapper
public interface OrderMapper {

    // CREATE
    int insertOrder(Order order);

    int insertItems(
        @Param("orderId") Long orderId,
        @Param("items") List<OrderItem> items
    );

    // READ
    OrderDetail findById(@Param("id") Long id);

    List<OrderSummary> findByCondition(
        @Param("filter") OrderSearchCondition filter,
        @Param("limit") int limit,
        @Param("offset") int offset
    );

    long countByCondition(
        @Param("filter") OrderSearchCondition filter
    );

    boolean existsById(@Param("id") Long id);

    List<OrderSummary> findByIds(
        @Param("ids") List<Long> ids
    );

    // UPDATE
    int updateStatusIfVersion(
        @Param("id") Long id,
        @Param("expectedVersion") int expectedVersion,
        @Param("newStatus") String newStatus
    );

    int patchOrder(OrderPatch patch);

    // DELETE
    int softDeleteById(
        @Param("id") Long id,
        @Param("version") int version
    );

    int hardDeleteById(@Param("id") Long id);
}
```

예제에서 사용하는 모델은 다음과 같은 필드를 갖는 일반 Java Bean이라고 가정합니다. 기본 생성자와 getter/setter가 준비되어 있어야 합니다.

| 클래스                    | 주요 필드                                                                                    |
| ---------------------- | ---------------------------------------------------------------------------------------- |
| `Order`                | `id`, `userId`, `status`, `totalAmount`, `shippingAddress`, `memo`, `version`            |
| `OrderItem`            | `id`, `productName`, `quantity`, `unitPrice`                                             |
| `OrderDetail`          | `id`, `status`, `totalAmount`, `shippingAddress`, `memo`, `version`, `customer`, `items` |
| `CustomerSummary`      | `id`, `name`, `email`                                                                    |
| `OrderSummary`         | `id`, `userId`, `status`, `totalAmount`, `createdAt`                                     |
| `OrderSearchCondition` | `userId`, `status`, `createdFrom`, `createdTo`, `keyword`                                |
| `OrderPatch`           | `id`, `version`, `shippingAddress`, `memo`                                               |

금액은 `BigDecimal`, 일시는 `LocalDateTime`, ID는 `Long`, 수량과 버전은 `int`, 나머지 문자열 필드는 `String`으로 둡니다. `OrderDetail.customer`는 `CustomerSummary`, `items`는 `List<OrderItem>`입니다. 검색 메서드에는 필드가 모두 비어 있어도 `null`이 아닌 `OrderSearchCondition`을 전달합니다.

### 4.2 Mapper XML의 기본 형태

```xml
<?xml version="1.0" encoding="UTF-8" ?>
<!DOCTYPE mapper
  PUBLIC "-//mybatis.org//DTD Mapper 3.0//EN"
  "https://mybatis.org/dtd/mybatis-3-mapper.dtd">

<mapper namespace="com.example.order.OrderMapper">

    <select id="findById">
        ...
    </select>

    <insert id="insertOrder">
        ...
    </insert>

    <update id="patchOrder">
        ...
    </update>

    <delete id="hardDeleteById">
        ...
    </delete>

</mapper>
```

여기서 중요한 것은 `namespace`와 `id`입니다.

- `namespace`: Mapper 인터페이스의 전체 클래스 이름
- `id`: 해당 인터페이스에 정의된 메서드 이름
- `select`, `insert`, `update`, `delete`: 수행할 SQL의 종류

Spring Boot 애플리케이션에 MyBatis Spring Boot Starter와 MySQL JDBC 드라이버를 추가하고 데이터 소스를 설정합니다. `application.properties`에 `mybatis.mapper-locations=classpath:mappers/OrderMapper.xml`을 지정하면 XML을 읽습니다. 애플리케이션의 기본 검색 패키지 아래에 있는 `@Mapper` 인터페이스는 Starter가 등록합니다. [MyBatis Spring Boot Starter](https://mybatis.org/spring-boot-starter/mybatis-spring-boot-autoconfigure/) 이후 XML 코드 블록은 별도 설명이 없으면 위 `<mapper>` 내부에 작성합니다. `<mapper>` 예제의 생략 기호는 아래 절의 SQL 정의가 들어갈 자리입니다.

### 4.3 자주 사용하는 속성

| 속성                 | 설명                                |
| ------------------ | --------------------------------- |
| `id`               | Mapper 메서드와 연결되는 SQL 식별자          |
| `parameterType`    | 입력 파라미터 타입. 생략 가능                 |
| `resultType`       | 조회 결과를 매핑할 Java 객체 타입             |
| `resultMap`        | 미리 정의한 결과 매핑 규칙                   |
| `useGeneratedKeys` | DB에서 자동 생성한 키를 가져올지 여부            |
| `keyProperty`      | 생성된 키를 저장할 Java 객체 프로퍼티           |
| `keyColumn`        | 생성 키에 해당하는 DB 컬럼                  |
| `timeout`          | JDBC 실행 타임아웃(초)                   |
| `fetchSize`        | JDBC 드라이버에 전달하는 조회 배치 크기 힌트       |
| `statementType`    | JDBC Statement 종류. 기본값 `PREPARED` |

각 `<select>`에는 `resultType`과 `resultMap` 중 하나를 지정합니다. 목록 조회의 `resultType`에는 목록 요소인 `OrderSummary`를 지정합니다.

## 5. Create — 데이터 생성

회원 ID 10이 `users`에 저장되어 있다고 가정합니다. 주문 한 건을 저장한 뒤 생성된 기본 키로 상품 목록을 저장합니다.

### 5.1 insertOrder — 주문 단건 생성

**Mapper XML**

```xml
<insert id="insertOrder"
        parameterType="com.example.order.Order"
        useGeneratedKeys="true"
        keyProperty="id">

    INSERT INTO orders (
        user_id,
        status,
        total_amount,
        shipping_address,
        memo
    )
    VALUES (
        #{userId},
        #{status},
        #{totalAmount},
        #{shippingAddress},
        #{memo,jdbcType=VARCHAR}
    )

</insert>
```

Service 또는 호출 코드의 실행 예시입니다.

```java
Order order = new Order();

order.setUserId(10L);
order.setStatus("PENDING");
order.setTotalAmount(new BigDecimal("35000.00"));
order.setShippingAddress("서울시 강남구");
order.setMemo("문 앞에 놓아주세요.");

int rows = orderMapper.insertOrder(order);

Long generatedId = order.getId();
```

생성 키와 파라미터 바인딩을 확인합니다.

`#{userId}`는 Java 객체의 `userId` 프로퍼티를 읽어 JDBC `PreparedStatement` 파라미터로 전달합니다.

내부적으로는 다음과 유사한 SQL이 실행됩니다.

```sql
INSERT INTO orders (
    user_id,
    status,
    total_amount,
    shipping_address,
    memo
)
VALUES (?, ?, ?, ?, ?)
```

Mapper XML의 두 속성이 생성 키를 받을 프로퍼티를 지정합니다.

```text
useGeneratedKeys="true"
keyProperty="id"
```

INSERT 이후 데이터베이스가 생성한 PK를 Java 객체의 `id` 필드에 저장합니다.

주의할 점은 반환값의 의미입니다.

| 값               | 의미                 |
| --------------- | ------------------ |
| `int rows`      | INSERT로 영향을 받은 행 수 |
| `order.getId()` | DB가 생성한 주문 PK      |

### 5.2 insertItems — 주문 상품 다건 생성

주문에는 여러 상품이 포함될 수 있습니다.

**Mapper XML**

```xml
<insert id="insertItems">

    INSERT INTO order_items (
        order_id,
        product_name,
        quantity,
        unit_price
    )
    VALUES

    <foreach collection="items"
             item="item"
             separator=",">

        (
            #{orderId},
            #{item.productName},
            #{item.quantity},
            #{item.unitPrice}
        )

    </foreach>

</insert>
```

생성된 주문 ID가 100이고 상품 목록에 세 건이 있으면 다음 SQL이 만들어집니다. 실제 실행에서는 각 값이 `?`에 바인딩됩니다.

```sql
INSERT INTO order_items (
    order_id,
    product_name,
    quantity,
    unit_price
)
VALUES
    (100, '키보드', 1, 15000),
    (100, '마우스', 2, 5000),
    (100, 'USB 허브', 1, 10000);
```

`foreach`의 역할은 컬렉션을 순회하면서 SQL 조각을 반복 생성하는 것입니다.

| 속성           | 설명                  |
| ------------ | ------------------- |
| `collection` | 순회할 컬렉션             |
| `item`       | 현재 요소를 참조할 변수       |
| `index`      | 현재 요소의 인덱스 또는 Map 키 |
| `open`       | 반복 SQL 앞에 붙일 문자열    |
| `separator`  | 각 요소 사이에 들어갈 문자열    |
| `close`      | 반복 SQL 뒤에 붙일 문자열    |

`insertItems()`를 호출할 때는 빈 리스트를 전달하지 않도록 서비스 계층에서 검사해야 합니다. 빈 리스트라면 `VALUES` 뒤에 실제 값이 없는 잘못된 SQL이 만들어질 수 있습니다.

`<foreach>`는 하나의 다중 행 INSERT 문을 만듭니다. 대량 데이터에서는 파라미터 개수와 SQL 크기를 고려해 적절한 크기로 나누는 것이 좋습니다.

### 5.3 실제 Service에서의 주문 생성

다음은 `OrderService.java`입니다. 메서드가 주문을 먼저 저장하고 생성된 ID를 상품 저장에 전달합니다.

```java
package com.example.order;

import java.util.List;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

@Service
public class OrderService {

    private final OrderMapper orderMapper;

    public OrderService(OrderMapper orderMapper) {
        this.orderMapper = orderMapper;
    }

    @Transactional
    public Long createOrder(
        Order order,
        List<OrderItem> items
    ) {
        if (items == null || items.isEmpty()) {
            throw new IllegalArgumentException(
                "주문 상품이 없습니다."
            );
        }

        orderMapper.insertOrder(order);

        orderMapper.insertItems(
            order.getId(),
            items
        );

        return order.getId();
    }
}
```

`@Transactional`이 중요한 이유는 주문 생성과 주문 상품 생성이 하나의 비즈니스 작업이기 때문입니다.

주문 INSERT 뒤 상품 INSERT에서 런타임 예외가 발생하면 Spring의 기본 트랜잭션 규칙에 따라 두 작업이 함께 롤백됩니다. 체크 예외를 사용하는 경우에는 필요한 롤백 규칙을 별도로 설정합니다. 트랜잭션은 Spring이 관리하는 Service 프록시를 통해 호출되어야 적용됩니다.

서비스에서는 이 로직 전에 회원, 상품, 가격, 수량을 검증하고, 주문 총액도 신뢰할 수 있는 상품 가격 정보를 기준으로 계산해야 합니다.

## 6. Read — 데이터 조회

상세 조회는 주문과 회원, 상품을 묶어 반환합니다. 목록 조회는 주문 요약을 반환하고 검색 건수는 별도 SQL로 계산합니다.

### 6.1 resultMap — 조회 결과와 객체 매핑

단건 상세 조회에 사용할 `resultMap`을 정의합니다.

```xml
<resultMap id="orderDetailMap"
           type="com.example.order.OrderDetail">

    <id property="id"
        column="order_id"/>

    <result property="status"
            column="order_status"/>

    <result property="totalAmount"
            column="order_total_amount"/>

    <result property="shippingAddress"
            column="order_shipping_address"/>

    <result property="memo"
            column="order_memo"/>

    <result property="version"
            column="order_version"/>

    <association property="customer"
                 javaType="com.example.order.CustomerSummary">

        <id property="id"
            column="customer_id"/>

        <result property="name"
                column="customer_name"/>

        <result property="email"
                column="customer_email"/>

    </association>

    <collection property="items"
                ofType="com.example.order.OrderItem">

        <id property="id"
            column="item_id"/>

        <result property="productName"
                column="item_product_name"/>

        <result property="quantity"
                column="item_quantity"/>

        <result property="unitPrice"
                column="item_unit_price"/>

    </collection>

</resultMap>
```

주요 태그들의 역할은 다음과 같습니다.

| 태그              | 설명                   |
| --------------- | -------------------- |
| `<resultMap>`   | 결과 매핑 규칙 정의          |
| `<id>`          | 객체를 식별하는 PK 컬럼 매핑    |
| `<result>`      | 일반 컬럼 매핑             |
| `<association>` | 1:1 또는 N:1 관계의 객체 매핑 |
| `<collection>`  | 1:N 관계의 컬렉션 매핑       |

`association`과 `collection`이 특히 중요합니다.

다음과 같은 조회 결과가 있다고 가정합니다.

| order_id | customer_name | item_id | item_product_name |
| -------- | ------------- | ------- | ----------------- |
| 100      | 김철수           | 1       | 키보드               |
| 100      | 김철수           | 2       | 마우스               |
| 100      | 김철수           | 3       | USB 허브            |

SQL 결과는 3행이지만, `resultMap`을 통해 하나의 주문 객체와 세 개의 주문 상품 객체로 구성할 수 있습니다.

```text
OrderDetail
  id: 100
  customer:
    name: 김철수
  items:
    - 키보드
    - 마우스
    - USB 허브
```

이때 각 객체의 `<id>` 매핑은 중복 행을 올바른 객체에 결합하는 데 중요합니다. 공식 문서에서도 JOIN 기반 중첩 결과 매핑에서 식별자 매핑을 명시할 것을 권장합니다.

### 6.2 findById — PK 기반 상세 조회

**Mapper XML**

```xml
<select id="findById"
        resultMap="orderDetailMap">

    SELECT
        o.id AS order_id,
        o.status AS order_status,
        o.total_amount AS order_total_amount,
        o.shipping_address AS order_shipping_address,
        o.memo AS order_memo,
        o.version AS order_version,

        u.id AS customer_id,
        u.name AS customer_name,
        u.email AS customer_email,

        oi.id AS item_id,
        oi.product_name AS item_product_name,
        oi.quantity AS item_quantity,
        oi.unit_price AS item_unit_price

    FROM orders o

    JOIN users u
      ON o.user_id = u.id

    LEFT JOIN order_items oi
      ON o.id = oi.order_id

    WHERE o.id = #{id}
      AND o.deleted_at IS NULL

    ORDER BY oi.id

</select>
```

Service에서 주문 ID로 상세 정보를 조회합니다.

```java
OrderDetail order = orderMapper.findById(100L);

if (order == null) {
    throw new IllegalArgumentException(
        "존재하지 않는 주문입니다."
    );
}
```

이 메서드는 주문 기본 정보, 회원 정보, 주문 상품을 한 번에 조회합니다.

`LEFT JOIN`을 사용하는 이유는 주문 상품이 없는 경우에도 주문 자체를 조회할 수 있도록 하기 위해서입니다.

복잡한 관계 매핑은 별도 SQL을 여러 번 호출하는 Nested Select 방식으로도 구성할 수 있지만, 조회 대상이 많으면 N+1 쿼리 문제가 발생할 수 있습니다.

단건 상세 조회처럼 조회 범위가 작은 경우 JOIN과 `resultMap`을 조합하는 방식이 실용적입니다.

### 6.3 findByCondition — 동적 조건 검색과 페이징

관리자 화면에서는 다음 조건으로 주문을 검색할 수 있습니다.

- 회원 ID
- 주문 상태
- 주문 생성 기간
- 배송 주소 또는 메모 키워드
- 페이지 번호와 페이지 크기

동적 SQL로 전달된 검색 조건만 추가합니다.

우선 재사용할 SQL을 작성합니다.

```xml
<sql id="orderSummaryColumns">
    o.id AS id,
    o.user_id AS userId,
    o.status AS status,
    o.total_amount AS totalAmount,
    o.created_at AS createdAt
</sql>
```

`<sql>`은 재사용 가능한 SQL 조각을 정의합니다.

이 SQL은 `<include>`를 사용하여 불러올 수 있습니다.

검색 조건을 별도 SQL 조각으로 정의합니다.

```xml
<sql id="orderSearchWhere">

    <where>
        o.deleted_at IS NULL

        <if test="filter.userId != null">
            AND o.user_id = #{filter.userId}
        </if>

        <if test="filter.status != null
                  and filter.status != ''">
            AND o.status = #{filter.status}
        </if>

        <if test="filter.createdFrom != null">
            AND o.created_at >= #{filter.createdFrom}
        </if>

        <if test="filter.createdTo != null">
            AND o.created_at &lt; #{filter.createdTo}
        </if>

        <if test="filter.keyword != null
                  and filter.keyword != ''">

            <bind name="keywordPattern"
                  value="'%' + filter.keyword + '%'"/>

            AND (
                o.shipping_address LIKE #{keywordPattern}
                OR o.memo LIKE #{keywordPattern}
            )

        </if>

    </where>

</sql>
```

여기에는 Dynamic SQL에서 자주 사용하는 태그가 세 가지 포함되어 있습니다.

`<if>`

조건을 만족하는 경우에만 SQL을 추가합니다.

```xml
<if test="filter.status != null and filter.status != ''">
    AND o.status = #{filter.status}
</if>
```

예를 들어 `status`가 `PAID`라면 상태 조건이 추가되고, `null`이나 빈 문자열이면 상태 조건을 생략합니다.

`<where>`

조건이 존재할 때 `WHERE`를 생성하고, 조건의 맨 앞에 있는 불필요한 `AND`, `OR`를 정리합니다.

`<bind>`

OGNL 표현식으로 계산한 값을 새로운 변수로 등록합니다.

```xml
<bind name="keywordPattern"
      value="'%' + filter.keyword + '%'"/>
```

사용자가 `서울`을 입력하면 `%서울%`이라는 검색 패턴을 만들어 `#{keywordPattern}`에 전달합니다.

검색 SQL은 두 조각을 포함합니다.

```xml
<select id="findByCondition"
        resultType="com.example.order.OrderSummary">

    SELECT
        <include refid="orderSummaryColumns"/>

    FROM orders o

    <include refid="orderSearchWhere"/>

    ORDER BY o.created_at DESC, o.id DESC

    LIMIT #{limit}
    OFFSET #{offset}

</select>
```

다음과 같이 호출할 수 있습니다.

```java
OrderSearchCondition filter =
    new OrderSearchCondition();

filter.setUserId(10L);
filter.setStatus("PAID");
filter.setKeyword("서울");

int page = 2;
int size = 20;

int offset = (page - 1) * size;

List<OrderSummary> orders =
    orderMapper.findByCondition(
        filter,
        size,
        offset
    );
```

다음은 입력값을 이해하기 쉽게 표시한 SQL입니다. 실제 실행에서는 값이 `?`에 바인딩됩니다.

```sql
SELECT
    o.id AS id,
    o.user_id AS userId,
    o.status AS status,
    o.total_amount AS totalAmount,
    o.created_at AS createdAt
FROM orders o
WHERE o.deleted_at IS NULL
  AND o.user_id = 10
  AND o.status = 'PAID'
  AND (
      o.shipping_address LIKE '%서울%'
      OR o.memo LIKE '%서울%'
  )
ORDER BY o.created_at DESC, o.id DESC
LIMIT 20 OFFSET 20;
```

페이지 번호는 1부터 시작한다고 가정했습니다.

실무에서는 `limit`의 최댓값과 `offset`의 범위를 서비스에서 검증해야 합니다. 또한 목록 페이징에 1:N JOIN을 직접 적용하면 JOIN으로 증가한 행에 LIMIT가 적용되어 주문 개수가 기대와 달라질 수 있습니다. 따라서 **목록은 요약 정보로 조회하고, 상세 정보는 별도 조회하는 방식**이 안전합니다.

### 6.4 countByCondition — 조건 검색 결과 건수 조회

페이징 기능에서는 데이터 목록뿐 아니라 전체 결과 건수가 필요합니다.

**Mapper XML**

```xml
<select id="countByCondition"
        resultType="long">

    SELECT COUNT(*)

    FROM orders o

    <include refid="orderSearchWhere"/>

</select>
```

`findByCondition`과 동일한 검색 조건을 사용하므로, 목록과 전체 건수의 검색 기준이 일치합니다.

```java
List<OrderSummary> orders =
    orderMapper.findByCondition(
        filter, 20, 0
    );

long totalCount =
    orderMapper.countByCondition(filter);
```

실무에서 `<sql>`과 `<include>`를 사용하는 대표적인 사례입니다.

특히 검색 조건이 변경될 때 두 쿼리에 동일하게 반영할 수 있어 유지보수에 유리합니다.

### 6.5 existsById — 데이터 존재 여부 조회

주문이 실제로 존재하는지 확인할 때 사용하는 메서드입니다.

**Mapper XML**

```xml
<select id="existsById"
        resultType="boolean">

    SELECT EXISTS (
        SELECT 1
        FROM orders
        WHERE id = #{id}
          AND deleted_at IS NULL
    )

</select>
```

Service에서 주문 ID로 존재 여부를 확인합니다.

```java
boolean exists = orderMapper.existsById(100L);
```

MySQL에서 `EXISTS`는 조건에 맞는 데이터가 존재하면 1, 없으면 0을 반환합니다. MyBatis는 이를 Java `boolean`으로 매핑할 수 있습니다.

존재 여부만 필요한 상황에서는 전체 객체를 조회하는 것보다 목적이 명확한 메서드입니다.

존재 여부를 조회한 뒤 다른 트랜잭션이 같은 주문을 삭제할 수 있습니다. 수정 성공 여부는 버전 조건과 수정 SQL의 영향 행 수로 판단합니다.

### 6.6 findByIds — 여러 ID를 한 번에 조회

여러 주문의 ID를 받아 한 번에 조회하는 기능입니다.

**Mapper XML**

```xml
<select id="findByIds"
        resultType="com.example.order.OrderSummary">

    SELECT
        <include refid="orderSummaryColumns"/>

    FROM orders o

    WHERE o.deleted_at IS NULL

    <choose>

        <when test="ids != null and ids.size() > 0">

            AND o.id IN

            <foreach collection="ids"
                     item="id"
                     open="("
                     separator=","
                     close=")">
                #{id}
            </foreach>

        </when>

        <otherwise>
            AND 1 = 0
        </otherwise>

    </choose>

</select>
```

Service에서 조회할 주문 ID 목록을 전달합니다.

```java
List<Long> ids = List.of(100L, 101L, 102L);

List<OrderSummary> orders =
    orderMapper.findByIds(ids);
```

생성 SQL의 SELECT 목록은 `orderSummaryColumns` 조각과 같으며, 아래에서는 생략합니다.

```sql
SELECT ...
FROM orders o
WHERE o.deleted_at IS NULL
  AND o.id IN (100, 101, 102);
```

여기서는 `<choose>`를 이용해 빈 컬렉션에 대한 안전장치를 추가했습니다.

| 상황        | 생성되는 조건                 |
| --------- | ----------------------- |
| ID가 존재    | `AND o.id IN (?, ?, ?)` |
| ID가 비어 있음 | `AND 1 = 0`             |

빈 리스트가 전달되었을 때 모든 주문이 조회되는 상황을 막기 위해서입니다.

참고로 `<choose>`는 Java의 `switch` 또는 `if-else if-else`와 비슷한 역할을 합니다. 여러 `<when>` 중 처음 참이 되는 조건 하나를 선택하며, 만족하는 조건이 없다면 `<otherwise>`를 사용합니다.

## 7. Update — 데이터 수정

Update에서 흔히 필요한 메서드는 특정 컬럼 변경, 일부 필드 수정, 조건부 수정입니다.

### 7.1 updateStatusIfVersion — 주문 상태 변경

**Mapper XML**

```xml
<update id="updateStatusIfVersion">

    UPDATE orders

    SET
        status = #{newStatus},
        version = version + 1

    WHERE id = #{id}
      AND version = #{expectedVersion}
      AND deleted_at IS NULL

</update>
```

여기서 `version`은 낙관적 락을 위한 컬럼입니다. 영향 행 수가 0이면 버전 충돌뿐 아니라 주문이 없거나 이미 논리 삭제된 경우도 포함하므로 서비스에서 실패로 처리하고 필요하면 원인을 확인합니다.

예를 들어 주문의 현재 데이터가 다음과 같다고 가정합니다.

```text
id      = 100
status  = PENDING
version = 3
```

두 요청이 동시에 같은 주문을 수정하려고 합니다.

| 순서 | 요청 A           | 요청 B                  |
| -- | -------------- | --------------------- |
| 1  | version=3 조회   | version=3 조회          |
| 2  | UPDATE 실행      |                       |
| 3  | version이 4로 변경 |                       |
| 4  |                | version=3으로 UPDATE 시도 |
| 결과 | 성공, 영향받은 행 1개  | 실패, 영향받은 행 0개         |

호출 인자가 `id=100`, `expectedVersion=3`, `newStatus="PAID"`이면 SQL에는 자리표시자 순서대로 `PAID`, `100`, `3`이 바인딩됩니다.

```sql
UPDATE orders SET status = ?, version = version + 1
WHERE id = ? AND version = ? AND deleted_at IS NULL;
```

```java
int updated = orderMapper.updateStatusIfVersion(
    100L,
    3,
    "PAID"
);

if (updated == 0) {
    throw new IllegalStateException(
        "주문이 존재하지 않거나 다른 요청에 의해 변경되었습니다."
    );
}
```

서비스에서 주문 상태 전이 규칙도 별도로 검사해야 합니다. 예를 들어 이미 배송 완료된 주문을 다시 결제 대기 상태로 변경하지 못하게 하는 것은 Mapper보다는 비즈니스 계층의 책임입니다.

### 7.2 patchOrder — 전달된 필드만 부분 수정

수정 API에서는 모든 필드를 한 번에 변경하지 않는 경우가 많습니다.

예를 들어 주문의 배송 주소만 변경할 수 있습니다.

**Mapper XML**

```xml
<update id="patchOrder">

    UPDATE orders

    <set>

        <if test="shippingAddress != null">
            shipping_address = #{shippingAddress},
        </if>

        <if test="memo != null">
            memo = #{memo},
        </if>

        version = version + 1

    </set>

    WHERE id = #{id}
      AND version = #{version}
      AND deleted_at IS NULL

</update>
```

`<set>`은 동적으로 UPDATE의 SET 절을 생성합니다.

다음 데이터가 전달되었다고 가정합니다.

```java
OrderPatch patch = new OrderPatch();

patch.setId(100L);
patch.setVersion(3);
patch.setShippingAddress("서울시 송파구");
patch.setMemo(null);
```

다음은 입력값을 표시한 결과 SQL입니다. 실제 실행에서는 값이 `?`에 바인딩됩니다.

```sql
UPDATE orders
SET
    shipping_address = '서울시 송파구',
    version = version + 1
WHERE id = 100
  AND version = 3
  AND deleted_at IS NULL;
```

`shippingAddress`와 `memo`는 각각 `null`이면 변경되지 않습니다. 이 예제에서는 `memo`만 변경되지 않습니다.

`<set>`의 중요한 특징은 다음과 같습니다.

- 수정할 필드가 있을 때 `SET` 키워드를 생성
- 마지막에 불필요하게 남는 쉼표 제거
- `<if>`를 사용하여 수정 대상 필드를 동적으로 결정

위 예제에서는 버전 증가 구문이 항상 존재하므로 SET 절 자체가 비는 문제는 없지만, 수정할 데이터가 전혀 없는 요청은 서비스에서 거부하는 것이 좋습니다.

메모를 실제로 NULL로 초기화해야 한다면 `clearMemo`와 같은 전용 메서드나, 필드가 전달되었는지 구분하는 별도 플래그를 사용하는 것이 좋습니다.

### 7.3 **`<trim>`** — 동적 UPDATE를 직접 제어

`<set>`의 동작이 필요한 형태와 맞지 않는다면 `<trim>`으로 대체할 수 있습니다.

```xml
<trim prefix="SET" suffixOverrides=",">

    <if test="shippingAddress != null">
        shipping_address = #{shippingAddress},
    </if>

    <if test="memo != null">
        memo = #{memo},
    </if>

    version = version + 1,

</trim>
```

`patchOrder`의 `<set>` 전체를 이 조각으로 바꿀 수 있습니다. MyBatis가 앞에 `SET`을 추가하고 끝의 쉼표를 제거합니다.

`<trim>`은 뒤에서 살펴볼 `<where>`의 동작도 대체할 수 있는 범용적인 SQL 정리 태그입니다.

## 8. Delete — 데이터 삭제

서비스에서는 데이터를 실제로 삭제하는 Hard Delete와 삭제된 것처럼 표시하는 Soft Delete를 구분하는 경우가 많습니다.

### 8.1 softDeleteById — 논리 삭제

**Mapper XML**

```xml
<update id="softDeleteById">

    UPDATE orders

    SET
        deleted_at = CURRENT_TIMESTAMP,
        version = version + 1

    WHERE id = #{id}
      AND version = #{version}
      AND deleted_at IS NULL

</update>
```

`softDeleteById`는 삭제 시각을 기록하고 버전을 올립니다.

삭제 전에는 `deleted_at`이 비어 있습니다.

```text
id = 100
deleted_at = NULL
```

삭제 후에는 `deleted_at`에 삭제 시각이 남습니다.

```text
id = 100
deleted_at = 2026-11-22 15:30:00
```

데이터베이스에는 레코드가 남아 있지만 일반적인 조회에서는 `deleted_at IS NULL` 조건으로 제외합니다.

이 방식은 다음과 같은 서비스에 적합합니다.

- 삭제 이력 관리
- 복구 기능이 필요한 서비스
- 거래 및 주문 기록을 보존해야 하는 시스템

중요한 점은 Soft Delete를 도입하면 조회 및 수정 SQL에서도 삭제 상태를 일관되게 확인해야 한다는 것입니다.

### 8.2 hardDeleteById — 물리 삭제

**Mapper XML**

```xml
<delete id="hardDeleteById">

    DELETE FROM orders
    WHERE id = #{id}

</delete>
```

실제 DB에서 해당 주문을 삭제합니다.

예제 DDL에서 `order_items`의 외래 키에 `ON DELETE CASCADE`를 설정했기 때문에 주문을 삭제하면 관련 주문 상품도 함께 삭제됩니다.

만약 CASCADE를 사용하지 않는 구조라면 다음처럼 자식 데이터를 먼저 삭제해야 할 수 있습니다.

```sql
DELETE FROM order_items WHERE order_id = 100;

DELETE FROM orders WHERE id = 100;
```

이 경우에도 두 SQL은 하나의 트랜잭션에서 실행되어야 합니다.

실무에서는 Hard Delete를 사용자 요청에 바로 연결하기보다, 법적 보관 의무와 감사 요건을 검토하고 별도의 관리 기능으로 제한하는 경우가 많습니다.

## 9. Dynamic SQL 핵심 태그 정리

동적 SQL 태그는 조건을 평가하고, 컬렉션을 순회하고, SQL 절의 앞뒤 문자열을 정리합니다.

| 태그            | 역할                      | 자주 사용하는 메서드                     |
| ------------- | ----------------------- | ------------------------------- |
| `<if>`        | 조건이 참일 때만 SQL 생성        | `findByCondition`, `patchOrder` |
| `<choose>`    | 여러 조건 중 하나 선택           | 우선순위 검색, 빈 리스트 처리               |
| `<when>`      | choose의 조건 분기           | `findByIds`                     |
| `<otherwise>` | 기본 분기                   | `findByIds`                     |
| `<where>`     | WHERE 생성 및 앞쪽 AND/OR 제거 | 동적 조건 검색                        |
| `<set>`       | SET 생성 및 마지막 쉼표 제거      | 부분 수정                           |
| `<trim>`      | SQL 접두어/접미어 정리          | 복잡한 동적 WHERE/UPDATE             |
| `<foreach>`   | 컬렉션 반복 처리               | 다건 INSERT, IN 검색                |
| `<bind>`      | OGNL 표현식으로 변수 생성        | LIKE 검색                         |

### 9.1 **`<where>`**와 **`<trim>`**의 관계

다음 두 코드는 `status` 파라미터를 받는 매퍼의 WHERE 절에 넣는 대안입니다.

where 사용

```xml
<where>
    <if test="status != null">
        AND status = #{status}
    </if>
</where>
```

trim 사용

```xml
<trim prefix="WHERE"
      prefixOverrides="AND |OR ">

    <if test="status != null">
        AND status = #{status}
    </if>

</trim>
```

`prefixOverrides`는 지정된 문자열이 앞에 등장하면 제거합니다. 여기서 공백도 의미가 있습니다.

### 9.2 **`<set>`**과 **`<trim>`**의 관계

```xml
<set>
    <if test="name != null">
        name = #{name},
    </if>
</set>
```

이는 `name` 파라미터를 받는 별도 UPDATE의 SET 절에서 다음 `trim` 구조로 대체할 수 있습니다.

```xml
<trim prefix="SET"
      suffixOverrides=",">

    <if test="name != null">
        name = #{name},
    </if>

</trim>
```

`prefix`는 앞에 추가할 문자열, `suffixOverrides`는 끝에서 제거할 문자열을 의미합니다.

### 9.3 **`<choose>`** — 조건의 우선순위 지정

복수의 조건 중 하나만 적용해야 할 때 사용합니다.

예를 들어 `orderId`와 `userId` 파라미터를 받는 별도 SELECT의 WHERE 절에서 ID를 우선하여 검색하고, 없다면 회원 ID로 검색할 수 있습니다.

```xml
<choose>

    <when test="orderId != null">
        AND id = #{orderId}
    </when>

    <when test="userId != null">
        AND user_id = #{userId}
    </when>

    <otherwise>
        AND 1 = 0
    </otherwise>

</choose>
```

`orderId`와 `userId`가 모두 존재하더라도 첫 번째 조건만 적용됩니다.

참고로 `<if>`는 조건들이 각각 독립적으로 평가되므로 여러 조건이 동시에 적용될 수 있습니다.

### 9.4 **`<foreach>`** — IN 조건 처리

```xml
<foreach collection="ids"
         item="id"
         open="("
         separator=","
         close=")">
    #{id}
</foreach>
```

ID가 세 개라면 다음과 같이 생성됩니다.

```text
(100, 101, 102)
```

Map, 배열, `Iterable` 타입도 순회할 수 있습니다. 위 블록은 `ids`라는 파라미터를 받는 매퍼의 `IN` 절에 넣는 조각입니다.

단, DELETE나 UPDATE의 WHERE 절에서 `foreach`를 사용하는 경우 빈 컬렉션 때문에 삭제·수정 범위가 넓어지지 않도록 특별히 주의해야 합니다.

## 10. SQL 파라미터와 결과 매핑에서 반드시 알아야 할 개념

### 10.1 **`#{}`**와 **`${}`**의 차이

MyBatis에서 가장 중요한 문법 차이 중 하나입니다.

| 구분                        | `#{}`         | `${}`         |
| ------------------------- | ------------- | ------------- |
| 처리 방식                     | JDBC 파라미터 바인딩 | SQL 문자열 직접 치환 |
| PreparedStatement의 `?` 사용 | 예             | 아니요           |
| SQL Injection 위험          | 값 바인딩 시 낮음    | 외부 입력을 넣으면 높음 |
| 일반 값 조건                   | 권장            | 사용하지 않는 것이 좋음 |
| 동적 컬럼명/테이블명               | 직접 사용 불가      | 제한적으로 가능      |

다음 예제를 살펴봅니다.

```sql
WHERE id = #{id}
```

JDBC에 전달되는 SQL에는 값 자리에 `?`가 들어갑니다.

```sql
WHERE id = ?
```

`${}` 치환은 변수 내용을 SQL에 그대로 삽입합니다.

```sql
ORDER BY ${sortColumn}
```

따라서 `sortColumn`에 사용자 입력을 검증 없이 전달하면 SQL Injection 위험이 있습니다.

`sort` 파라미터를 받는 별도 SELECT의 정렬 절은 다음과 같이 허용된 값만 SQL에 반영하는 편이 안전합니다.

```xml
ORDER BY

<choose>

    <when test="sort == 'oldest'">
        o.created_at ASC
    </when>

    <otherwise>
        o.created_at DESC
    </otherwise>

</choose>
```

공식 문서 역시 `${}`에 사용자 입력을 그대로 전달하지 않도록 경고합니다.

### 10.2 **`@Param`**은 언제 사용하는가?

여러 파라미터를 전달할 때 명확한 이름을 지정하기 위해 사용합니다.

```java
OrderDetail findById(@Param("id") Long id);
```

Mapper XML에서 이름을 그대로 참조합니다.

```sql
WHERE id = #{id}
```

복수 파라미터에도 이름을 부여할 수 있습니다.

```java
int updateStatus(
    @Param("id") Long id,
    @Param("status") String status
);
```

Mapper XML에서 이름을 그대로 참조합니다.

```sql
WHERE id = #{id}
```

```text
SET status = #{status}
```

단일 Java Bean 객체를 전달한다면 일반적으로 프로퍼티 이름을 바로 사용할 수 있습니다.

```java
int insertOrder(Order order);
```

Mapper XML에서 이름을 그대로 참조합니다.

```text
#{userId}
#{status}
#{totalAmount}
```

복수 파라미터에서는 `@Param`을 명시하여 이름 의존성을 줄이는 것을 추천합니다.

### 10.3 `resultType`과 `resultMap`

**resultType**

쿼리 결과를 단순한 Java 객체로 매핑할 때 사용합니다.

```xml
<select id="findSimpleOrder"
        resultType="com.example.order.Order">

    SELECT
        id,
        user_id AS userId,
        status,
        total_amount AS totalAmount,
        shipping_address AS shippingAddress,
        memo,
        version

    FROM orders
    WHERE id = #{id}

</select>
```

**resultMap**

DB 컬럼과 Java 프로퍼티가 다르거나, JOIN 결과를 복잡한 객체 구조로 매핑해야 할 때 사용합니다.

```xml
<resultMap id="simpleOrderMap"
           type="com.example.order.Order">

    <id property="id" column="id"/>

    <result property="userId"
            column="user_id"/>

    <result property="totalAmount"
            column="total_amount"/>

</resultMap>
```

DB에서 `snake_case`, Java에서 `camelCase`를 사용하는 경우 MyBatis 설정의 `mapUnderscoreToCamelCase`를 활성화하면 자동 매핑할 수도 있습니다.

```text
mybatis:
  configuration:
    map-underscore-to-camel-case: true
```

이 설정을 활성화하면 `user_id`와 `userId` 같은 이름을 자동 연결할 수 있습니다.

다만 복잡한 JOIN 조회에서는 명시적인 `resultMap`과 고유한 컬럼 별칭을 사용하는 것이 안전합니다.

### 10.4 **`jdbcType`**과 NULL 처리

공식 문서에서는 NULL 값을 JDBC 파라미터로 전달할 때 타입 정보를 지정할 수 있다고 설명합니다.

예를 들면 다음과 같습니다.

```text
#{memo,jdbcType=VARCHAR}
```

MyBatis는 Java 값의 타입을 대부분 자동 추론하지만, NULL 처리에서 드라이버 특성에 따라 JDBC 타입 지정이 필요할 수 있습니다.

Map 기반 파라미터나 사용자 정의 타입을 활용할 때는 `javaType`, `jdbcType`, `typeHandler` 등의 설정도 사용할 수 있습니다.

## 11. 공식 문서의 나머지 주요 기능

지금까지 설명한 기능 외에도 공식 문서에는 다음 기능을 제공합니다.

| 기능                | 설명                       | 활용 상황                |
| ----------------- | ------------------------ | -------------------- |
| `<selectKey>`     | INSERT 전후에 별도 SQL로 키 조회  | Sequence 기반 PK       |
| `<constructor>`   | 생성자로 조회 결과 매핑            | 불변 DTO               |
| `<discriminator>` | 조회 컬럼 값에 따라 결과 타입 선택     | 다형성 객체 매핑            |
| `columnPrefix`    | 중첩 결과 매핑의 컬럼 접두어 지정      | 동일 객체 타입을 여러 번 JOIN  |
| `select` 속성       | 다른 매핑 SQL로 연관 객체 조회      | Nested Select        |
| `_databaseId`     | DB 종류별로 동적 SQL 분기        | Oracle/MySQL 등 복수 DB |
| `<script>`        | 어노테이션 Mapper에서 동적 SQL 사용 | `@Select`, `@Update` |
| `lang`            | SQL 스크립트 언어 드라이버 선택      | 커스텀 SQL 처리           |

예를 들어 Oracle에서 Sequence 기반 키를 생성한다면 `selectKey`를 사용할 수 있습니다. 다음은 별도 Oracle Mapper의 `<mapper>` 내부에 넣는 예시입니다.

```xml
<insert id="insertWithSequence">

    <selectKey keyProperty="id"
               resultType="long"
               order="BEFORE">

        SELECT order_seq.NEXTVAL FROM dual

    </selectKey>

    INSERT INTO orders (
        id,
        user_id,
        status,
        total_amount,
        shipping_address
    )
    VALUES (
        #{id},
        #{userId},
        #{status},
        #{totalAmount},
        #{shippingAddress}
    )

</insert>
```

이 코드는 Oracle의 시퀀스용이며 앞서 정의한 MySQL `AUTO_INCREMENT` 스키마와 별개입니다.

또한 PostgreSQL처럼 INSERT와 함께 결과를 반환하는 `RETURNING` 구문을 사용할 경우, 공식 문서에서는 결과를 매핑하기 위해 `<select>`에 `affectData="true"`를 지정하는 방법을 설명합니다. 이 속성은 데이터를 변경하면서 결과 집합도 돌려주는 SQL에 사용합니다.

## 12. 실무에서 특히 주의할 점

| 항목                  | 주의할 점                                             |
| ------------------- | ------------------------------------------------- |
| 조건 없는 UPDATE/DELETE | WHERE 절이 누락되면 대량 변경이 발생할 수 있음                     |
| 빈 컬렉션               | `foreach`와 `IN` 사용 시 빈 리스트 처리 필요                  |
| 동적 SQL              | 조건이 모두 생략되어 의도치 않은 전체 조회가 발생하지 않는지 확인             |
| 다건 INSERT           | DB 파라미터 및 SQL 길이 제한 고려                            |
| 부분 수정               | NULL을 무시할지 실제 NULL로 변경할지 구분                       |
| 동시성                 | UPDATE 행 수와 version 조건 확인                         |
| 페이징                 | 정렬 기준을 명시하고 큰 OFFSET의 성능에 유의                      |
| JOIN 결과             | 중복 컬럼명에 별칭을 부여하고 중첩 결과의 ID 매핑 지정                  |
| 1:N 관계              | Nested Select의 N+1 문제와 JOIN 결과의 중복 행에 유의          |
| 트랜잭션                | 복수 INSERT/UPDATE가 하나의 비즈니스 작업이면 Service에서 트랜잭션 관리 |

추가로 MyBatis SQL을 작성할 때는 **생성된 SQL이 실제로 어떻게 완성되는지 확인하는 테스트**가 중요합니다. 특히 동적 SQL은 `null`, 빈 문자열, 빈 컬렉션, 여러 조건의 조합에 따라 전혀 다른 SQL이 생성됩니다.
