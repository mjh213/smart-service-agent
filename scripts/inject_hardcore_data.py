import json
import os
import sys

# 确保脚本能读取到项目根目录的模块
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.append(PROJECT_ROOT)

from config import config
from core.di_container import configure_standard_services, container

configure_standard_services(config)

from database.db_manager import db_manager
from database.knowledge_service import KnowledgeService


DEMO_CHANNEL_NAME = "pinduoduo"
DEMO_SHOP_ID = "shop_mock_admin_01"
DEMO_SHOP_NAME = "电商客服 Agent 演示店铺"
DEMO_USER_ID = "uid_mock_admin_01"
DEMO_USERNAME = "mock_admin_01"
DEMO_PASSWORD = "123456"


def ensure_demo_shop_and_account() -> dict:
    """补齐演示店铺和账号。"""
    db_manager.add_channel(DEMO_CHANNEL_NAME, "电商平台渠道")

    shop = db_manager.get_shop(DEMO_CHANNEL_NAME, DEMO_SHOP_ID)
    if not shop:
        db_manager.add_shop(
            channel_name=DEMO_CHANNEL_NAME,
            shop_id=DEMO_SHOP_ID,
            shop_name=DEMO_SHOP_NAME,
            shop_logo="",
            description="用于功能展示的本地演示店铺",
        )
        shop = db_manager.get_shop(DEMO_CHANNEL_NAME, DEMO_SHOP_ID)
    else:
        db_manager.update_shop_info(
            channel_name=DEMO_CHANNEL_NAME,
            shop_id=DEMO_SHOP_ID,
            shop_name=DEMO_SHOP_NAME,
            description="用于功能展示的本地演示店铺",
        )
        shop = db_manager.get_shop(DEMO_CHANNEL_NAME, DEMO_SHOP_ID)

    account = db_manager.get_account(DEMO_CHANNEL_NAME, DEMO_SHOP_ID, DEMO_USER_ID)
    if not account:
        db_manager.add_account(
            channel_name=DEMO_CHANNEL_NAME,
            shop_id=DEMO_SHOP_ID,
            user_id=DEMO_USER_ID,
            username=DEMO_USERNAME,
            password=DEMO_PASSWORD,
            cookies='{"is_mock": true}',
        )
        db_manager.update_account_status(
            channel_name=DEMO_CHANNEL_NAME,
            shop_id=DEMO_SHOP_ID,
            user_id=DEMO_USER_ID,
            status=1,
        )
    else:
        db_manager.update_account_info(
            channel_name=DEMO_CHANNEL_NAME,
            shop_id=DEMO_SHOP_ID,
            user_id=DEMO_USER_ID,
            username=DEMO_USERNAME,
            password=DEMO_PASSWORD,
            cookies='{"is_mock": true}',
            status=1,
        )

    return db_manager.get_shop(DEMO_CHANNEL_NAME, DEMO_SHOP_ID)


def ensure_keywords() -> None:
    """补齐演示用转人工关键词。"""
    for keyword in ["人工", "转人工", "退款", "退货", "投诉", "催发货", "售后"]:
        db_manager.add_keyword(keyword)


def seed_product_knowledge(service: KnowledgeService, db_shop_id: int) -> None:
    """注入商品知识。"""
    demo_products = [
        {
            "goods_id": 10001,
            "goods_name": "舒缓修护精华液 30ml",
            "price": "129-169元",
            "price_min": 12900,
            "price_max": 16900,
            "sold_quantity": 2680,
            "specifications": json.dumps(
                {"规格": ["30ml"], "适用肤质": ["敏感肌", "干燥肌"], "功效": ["舒缓", "修护", "保湿"]},
                ensure_ascii=False,
            ),
            "extracted_content": (
                "这款精华液主打舒缓泛红、修护屏障和长效保湿，核心成分包含神经酰胺、"
                "积雪草提取物和泛醇。适合敏感肌、换季泛红和熬夜后皮肤状态不稳定的人群。"
                "建议在爽肤水后取 2 到 3 滴全脸涂抹，早晚均可使用。"
            ),
        },
        {
            "goods_id": 10002,
            "goods_name": "氨基酸净润洁面慕斯 150ml",
            "price": "59-79元",
            "price_min": 5900,
            "price_max": 7900,
            "sold_quantity": 4125,
            "specifications": json.dumps(
                {"规格": ["150ml"], "适用肤质": ["油皮", "混合肌", "敏感肌"], "功效": ["温和清洁", "不紧绷"]},
                ensure_ascii=False,
            ),
            "extracted_content": (
                "这款洁面慕斯采用氨基酸表活体系，泡沫绵密，清洁后不易拔干。"
                "适合日常早晚清洁，尤其适合容易出油但又怕刺激的肤质。"
                "如果用户询问是否适合敏感肌，可以回答为温和型洁面，正常情况下可以使用。"
            ),
        },
        {
            "goods_id": 10003,
            "goods_name": "轻透防晒乳 SPF50+ PA++++",
            "price": "89-109元",
            "price_min": 8900,
            "price_max": 10900,
            "sold_quantity": 3560,
            "specifications": json.dumps(
                {"规格": ["50g"], "适用场景": ["通勤", "户外"], "特点": ["轻薄", "不假白", "成膜快"]},
                ensure_ascii=False,
            ),
            "extracted_content": (
                "这款防晒乳支持高倍防晒，质地轻薄，成膜速度快，适合日常通勤和户外短时活动。"
                "上脸不容易假白，后续叠加底妆也比较服帖。建议出门前 15 分钟使用，"
                "长时间户外场景每 2 到 3 小时补涂一次。"
            ),
        },
    ]

    for product in demo_products:
        service.add_or_update_product(
            shop_id=db_shop_id,
            goods_id=product["goods_id"],
            goods_name=product["goods_name"],
            price=product["price"],
            price_min=product["price_min"],
            price_max=product["price_max"],
            sold_quantity=product["sold_quantity"],
            specifications=product["specifications"],
            extracted_content=product["extracted_content"],
        )


def seed_customer_service_knowledge(service: KnowledgeService, db_shop_id: int) -> tuple[int, int]:
    """注入客服政策知识。"""
    rows = [
        {
            "title": "发货时效说明",
            "content": "常规订单在 48 小时内发出，预售或大促期间会以商品详情页说明为准。如用户着急收货，可建议其下单后备注并联系客服协助催发。",
            "tags": "发货,物流,时效",
        },
        {
            "title": "退换货规则",
            "content": "在不影响二次销售的前提下，商品签收后 7 天内支持无理由退换货；如商品存在质量问题，请引导用户提供照片，我们会优先安排售后处理。",
            "tags": "售后,退货,换货,退款",
        },
        {
            "title": "敏感肌咨询标准回复",
            "content": "当用户咨询敏感肌是否可用时，先建议查看成分和功效说明，再提醒用户结合自身肤质谨慎选择；如为首次使用，建议先做局部试用。",
            "tags": "敏感肌,成分,使用建议",
        },
        {
            "title": "人工客服接入说明",
            "content": "当用户连续追问订单异常、退款争议、投诉或情绪明显激动时，优先安抚用户情绪，并说明可为其转接人工客服继续跟进。",
            "tags": "人工,投诉,转人工",
        },
    ]
    return service.batch_import_customer_service(db_shop_id, rows)


def inject_mock_data() -> None:
    """向本地 SQLite 注入演示数据。"""
    print("开始向本地数据库注入电商客服 Agent 演示数据...")

    service = container.get(KnowledgeService)
    shop = ensure_demo_shop_and_account()
    ensure_keywords()

    db_shop_id = shop["id"]
    seed_product_knowledge(service, db_shop_id)
    success_count, skipped_count = seed_customer_service_knowledge(service, db_shop_id)

    print(f"演示店铺: {shop['shop_name']} ({shop['shop_id']})")
    print(f"演示账号: {DEMO_USERNAME} / {DEMO_PASSWORD}")
    print("商品知识: 已补齐 3 条演示商品")
    print(f"客服知识: 新增 {success_count} 条，跳过 {skipped_count} 条重复数据")
    print("转人工关键词: 已补齐常用演示词")
    print("")
    print("推荐演示方式：")
    print("1. 在账号管理界面添加 mock_admin_01 账号，可走免真实登录的演示流程。")
    print("2. 询问“这款精华液适合敏感肌吗”“多久发货”“可以退款吗”等问题测试知识检索。")
    print("3. 询问“帮我转人工”或“我要投诉”测试关键词转人工。")


if __name__ == "__main__":
    inject_mock_data()
