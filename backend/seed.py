from app.core.database import SessionLocal, engine, Base
from app.core.security import hash_password
from app.models.user import User
from app.models.directory import Directory
from app.models.field import Field
from app.models.mapping import DirectoryFieldMapping


def seed():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()

    try:
        # ── Users ──
        admin = db.query(User).filter(User.username == "admin").first()
        if not admin:
            admin = User(username="admin", hashed_password=hash_password("admin123"),
                         role="admin", display_name="系统管理员", email="admin@example.com")
            db.add(admin)
            db.commit()
            print("Default admin user created: admin / admin123")

        sample_users = [
            ("data_entry", "录入员"),
            ("data_admin", "数据管理员"),
            ("reviewer", "复核员"),
        ]
        for role, display_name in sample_users:
            if not db.query(User).filter(User.username == role).first():
                db.add(User(username=role, hashed_password=hash_password("admin123"),
                            role=role, display_name=display_name))
        db.commit()
        print("Sample users seeded.")

        # ── Directories ──
        if db.query(Directory).count() == 0:
            dirs_data = [
                {"name": "客户域", "code": "customer", "description": "客户相关数据资产", "level": 0},
                {"name": "客户基本信息", "code": "customer_base", "description": "客户姓名、证件等基础字段", "level": 1, "parent_code": "customer"},
                {"name": "客户联系信息", "code": "customer_contact", "description": "电话、邮箱、地址等", "level": 1, "parent_code": "customer"},
                {"name": "交易域", "code": "transaction", "description": "交易流水相关", "level": 0},
                {"name": "订单信息", "code": "order", "description": "订单头、订单行", "level": 1, "parent_code": "transaction"},
                {"name": "支付信息", "code": "payment", "description": "支付方式、流水号", "level": 1, "parent_code": "transaction"},
                {"name": "风控域", "code": "risk", "description": "风险控制相关", "level": 0},
                {"name": "反欺诈", "code": "anti_fraud", "description": "欺诈检测数据", "level": 1, "parent_code": "risk"},
            ]
            parent_map = {}
            for d in dirs_data:
                parent_id = None
                if "parent_code" in d:
                    parent_id = parent_map.get(d["parent_code"])
                obj = Directory(name=d["name"], code=d["code"], description=d.get("description", ""),
                                level=d["level"], parent_id=parent_id, created_by=admin.id)
                db.add(obj)
                db.flush()
                parent_map[d["code"]] = obj.id
            db.commit()
            print("Sample directories seeded.")

        # ── Fields ──
        if db.query(Field).count() == 0:
            fields_data = [
                {"field_code": "F001", "name": "客户姓名", "data_type": "VARCHAR", "table_name": "dim_customer", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L2"},
                {"field_code": "F002", "name": "身份证号", "data_type": "VARCHAR", "table_name": "dim_customer", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L4"},
                {"field_code": "F003", "name": "手机号", "data_type": "VARCHAR", "table_name": "dim_customer_contact", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L3"},
                {"field_code": "F004", "name": "邮箱", "data_type": "VARCHAR", "table_name": "dim_customer_contact", "database_name": "ods", "business_domain": "客户域", "sensitivity_level": "L2"},
                {"field_code": "F005", "name": "订单号", "data_type": "VARCHAR", "table_name": "fact_order", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L2"},
                {"field_code": "F006", "name": "订单金额", "data_type": "DECIMAL", "table_name": "fact_order", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L2"},
                {"field_code": "F007", "name": "支付方式", "data_type": "VARCHAR", "table_name": "dim_payment", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L1"},
                {"field_code": "F008", "name": "交易时间", "data_type": "DATETIME", "table_name": "fact_transaction", "database_name": "dw", "business_domain": "交易域", "sensitivity_level": "L2"},
                {"field_code": "F009", "name": "设备指纹", "data_type": "VARCHAR", "table_name": "fact_login", "database_name": "ods", "business_domain": "风控域", "sensitivity_level": "L3"},
                {"field_code": "F010", "name": "IP地址", "data_type": "VARCHAR", "table_name": "fact_login", "database_name": "ods", "business_domain": "风控域", "sensitivity_level": "L2"},
            ]
            for f in fields_data:
                db.add(Field(**f, created_by=admin.id))
            db.commit()
            print("Sample fields seeded.")

        # ── Mappings ──
        if db.query(DirectoryFieldMapping).count() == 0:
            dirs = {d.code: d.id for d in db.query(Directory).all()}
            fields = {f.field_code: f.id for f in db.query(Field).all()}
            mappings_data = [
                ("customer_base", "F001"), ("customer_base", "F002"),
                ("customer_contact", "F003"), ("customer_contact", "F004"),
                ("order", "F005"), ("order", "F006"),
                ("payment", "F007"), ("transaction", "F008"),
            ]
            for dir_code, field_code in mappings_data:
                did, fid = dirs.get(dir_code), fields.get(field_code)
                if did and fid:
                    db.add(DirectoryFieldMapping(directory_id=did, field_id=fid,
                                                 mapping_source="manual", created_by=admin.id))
            db.commit()
            print("Sample mappings seeded.")

        print("Seed completed.")
    finally:
        db.close()


if __name__ == "__main__":
    seed()
