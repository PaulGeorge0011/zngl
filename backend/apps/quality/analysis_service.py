import math
from collections import Counter
from datetime import datetime
from statistics import mean, pstdev
from typing import Iterable

from .models import Brand, MoistureData


DEFAULT_TARGET_MOISTURE = 12.40
DEFAULT_TOLERANCE = 0.50
DEFAULT_DIFF_LIMIT = 1.2


def _to_float(value):
    return None if value is None else float(value)


def _clean(values: Iterable):
    return [_to_float(value) for value in values if value is not None]


def _percent(count: int, total: int) -> float:
    if total <= 0:
        return 0.0
    return round(count * 100.0 / total, 2)


def _metric_summary(values: list[float]):
    if not values:
        return {'count': 0, 'min': None, 'max': None, 'avg': None, 'std': None}
    return {
        'count': len(values),
        'min': round(min(values), 3),
        'max': round(max(values), 3),
        'avg': round(mean(values), 3),
        'std': round(pstdev(values), 3) if len(values) > 1 else 0.0,
    }


def _top_items(counter: Counter, limit: int = 5):
    return [{'name': name or '未填写', 'count': count} for name, count in counter.most_common(limit)]


def _brand_threshold_map():
    return {
        brand.id: {
            'target': _to_float(brand.target_moisture) or DEFAULT_TARGET_MOISTURE,
            'tolerance': _to_float(brand.moisture_tolerance) or DEFAULT_TOLERANCE,
        }
        for brand in Brand.objects.all()
    }


def _threshold_for_brand(brand_id, brand_thresholds):
    config = brand_thresholds.get(brand_id, {})
    target = config.get('target', DEFAULT_TARGET_MOISTURE)
    tolerance = config.get('tolerance', DEFAULT_TOLERANCE)
    return target, tolerance, round(target - tolerance, 2), round(target + tolerance, 2)


def get_quality_queryset(brand_id=None):
    queryset = MoistureData.objects.select_related('brand').all()
    if brand_id:
        queryset = queryset.filter(brand_id=brand_id)
    return queryset.order_by('-id')


def build_quality_summary(brand_id=None):
    return build_quality_summary_from_queryset(get_quality_queryset(brand_id), brand_id=brand_id)


def detect_moisture_anomalies(brand_id=None, limit=50):
    return detect_moisture_anomalies_from_queryset(get_quality_queryset(brand_id), brand_id=brand_id, limit=limit)


def _report_queryset(report_date=None, brand_id=None):
    queryset = MoistureData.objects.select_related('brand').all()
    if brand_id:
        queryset = queryset.filter(brand_id=brand_id)

    if report_date:
        queryset_for_date = queryset.filter(sampling_date=report_date)
        if queryset_for_date.exists():
            return queryset_for_date.order_by('-id'), 'sampling_date', str(report_date)

    latest_sampling_date = (
        queryset.exclude(sampling_date__isnull=True)
        .order_by('-sampling_date')
        .values_list('sampling_date', flat=True)
        .first()
    )
    if latest_sampling_date:
        return queryset.filter(sampling_date=latest_sampling_date).order_by('-id'), 'sampling_date', str(latest_sampling_date)

    return queryset.order_by('-id')[:200], 'latest_snapshot', '最新数据快照'


def build_daily_report(report_date=None, brand_id=None):
    if isinstance(report_date, str) and report_date:
        report_date = datetime.strptime(report_date, '%Y-%m-%d').date()

    queryset, mode, label = _report_queryset(report_date=report_date, brand_id=brand_id)
    ids = list(queryset.values_list('id', flat=True))
    base_queryset = MoistureData.objects.filter(id__in=ids).order_by('-id')
    summary = build_quality_summary_from_queryset(base_queryset, brand_id=brand_id)
    anomalies = detect_moisture_anomalies_from_queryset(base_queryset, brand_id=brand_id, limit=10)

    metrics = summary['metrics']['finished_moisture']
    overview = summary['quality_overview']
    top_brand = summary['distributions']['brands'][0]['name'] if summary['distributions']['brands'] else '无'
    top_anomaly = anomalies['records'][0]['reasons'][0] if anomalies['records'] else '暂无明显异常'
    standard = summary['quality_overview']['standard']

    narrative = '\n'.join(
        [
            f'今日日报范围：{label}，共纳入 {summary["scope"]["total_records"]} 条记录。',
            f'当前判定标准默认按目标 {standard["target"]}，容差 ±{standard["tolerance"]}；若牌号已配置，则自动按牌号标准判定。',
            f'成品水分均值 {metrics["avg"]}，标准差 {metrics["std"]}，达标率 {overview["finished_in_range_pct"]}%。',
            f'主要牌号为 {top_brand}，高风险异常 {anomalies["summary"]["high_risk_count"]} 条，中风险异常 {anomalies["summary"]["medium_risk_count"]} 条。',
            f'当前最值得关注的问题是：{top_anomaly}。',
        ]
    )

    return {
        'report_date': str(report_date) if report_date else None,
        'report_mode': mode,
        'report_label': label,
        'summary': summary,
        'anomalies': anomalies,
        'narrative': narrative,
    }


def build_quality_summary_from_queryset(queryset, brand_id=None):
    rows = list(
        queryset.values(
            'id',
            'brand_id',
            'brand__name',
            'sampling_date',
            'sample_number',
            'machine_number',
            'machine_stage',
            'finished_moisture',
            'powder_rate',
            'addition_method',
            'batch_number',
            'shift',
            'drying_moisture',
            'mixed_moisture',
            'cabinet_moisture',
            'rolling_moisture',
        )
    )
    return _build_quality_summary_payload(rows, brand_id=brand_id)


def _build_quality_summary_payload(rows, brand_id=None):
    total = len(rows)
    finished_values = _clean(row['finished_moisture'] for row in rows)
    drying_values = _clean(row['drying_moisture'] for row in rows)
    mixed_values = _clean(row['mixed_moisture'] for row in rows)
    cabinet_values = _clean(row['cabinet_moisture'] for row in rows)
    rolling_values = _clean(row['rolling_moisture'] for row in rows)
    powder_values = _clean(row['powder_rate'] for row in rows)

    brand_counter = Counter(row['brand__name'] for row in rows)
    shift_counter = Counter(row['shift'] for row in rows)
    method_counter = Counter(row['addition_method'] for row in rows)
    machine_counter = Counter(row['machine_stage'] for row in rows)
    brand_thresholds = _brand_threshold_map()

    in_range_count = 0
    below_range_count = 0
    above_range_count = 0
    for row in rows:
        finished = _to_float(row['finished_moisture'])
        if finished is None:
            continue
        _, _, lower_bound, upper_bound = _threshold_for_brand(row['brand_id'], brand_thresholds)
        if finished < lower_bound:
            below_range_count += 1
        elif finished > upper_bound:
            above_range_count += 1
        else:
            in_range_count += 1

    return {
        'scope': {
            'brand_id': brand_id,
            'total_records': total,
            'distinct_brands': len(brand_counter),
        },
        'quality_overview': {
            'standard': {
                'target': DEFAULT_TARGET_MOISTURE,
                'tolerance': DEFAULT_TOLERANCE,
            },
            'finished_in_range_pct': _percent(in_range_count, len(finished_values)),
            'finished_below_range_count': below_range_count,
            'finished_above_range_count': above_range_count,
            'missing_sampling_date_count': sum(1 for row in rows if row['sampling_date'] is None),
            'missing_rolling_moisture_count': sum(1 for row in rows if row['rolling_moisture'] is None),
            'missing_cabinet_moisture_count': sum(1 for row in rows if row['cabinet_moisture'] is None),
            'missing_powder_rate_count': sum(1 for row in rows if row['powder_rate'] is None),
        },
        'metrics': {
            'finished_moisture': _metric_summary(finished_values),
            'drying_moisture': _metric_summary(drying_values),
            'mixed_moisture': _metric_summary(mixed_values),
            'cabinet_moisture': _metric_summary(cabinet_values),
            'rolling_moisture': _metric_summary(rolling_values),
            'powder_rate': _metric_summary(powder_values),
        },
        'distributions': {
            'brands': _top_items(brand_counter),
            'shifts': _top_items(shift_counter),
            'addition_methods': _top_items(method_counter),
            'machine_stages': _top_items(machine_counter),
        },
        'latest_samples': [
            {
                'id': row['id'],
                'brand_name': row['brand__name'],
                'sample_number': row['sample_number'],
                'sampling_date': row['sampling_date'],
                'machine_stage': row['machine_stage'],
                'shift': row['shift'],
                'finished_moisture': _to_float(row['finished_moisture']),
                'drying_moisture': _to_float(row['drying_moisture']),
                'mixed_moisture': _to_float(row['mixed_moisture']),
                'cabinet_moisture': _to_float(row['cabinet_moisture']),
            }
            for row in rows[:10]
        ],
    }


def detect_moisture_anomalies_from_queryset(queryset, brand_id=None, limit=50):
    rows = list(
        queryset.values(
            'id',
            'brand_id',
            'brand__name',
            'sampling_date',
            'sample_number',
            'machine_number',
            'machine_stage',
            'finished_moisture',
            'powder_rate',
            'addition_method',
            'batch_number',
            'shift',
            'drying_moisture',
            'mixed_moisture',
            'cabinet_moisture',
            'rolling_moisture',
        )
    )
    return _build_anomaly_payload(rows, brand_id=brand_id, limit=limit)


def _build_anomaly_payload(rows, brand_id=None, limit=50):
    finished_values = _clean(row['finished_moisture'] for row in rows)
    finished_mean = mean(finished_values) if finished_values else None
    finished_std = pstdev(finished_values) if len(finished_values) > 1 else 0.0
    brand_thresholds = _brand_threshold_map()
    records = []

    for row in rows:
        score = 0
        reasons = []
        finished = _to_float(row['finished_moisture'])
        drying = _to_float(row['drying_moisture'])
        mixed = _to_float(row['mixed_moisture'])
        cabinet = _to_float(row['cabinet_moisture'])
        powder_rate = _to_float(row['powder_rate'])
        target, tolerance, lower_bound, upper_bound = _threshold_for_brand(row['brand_id'], brand_thresholds)

        if finished is None:
            score += 20
            reasons.append('成品水分缺失')
        else:
            if finished < lower_bound:
                score += 40
                reasons.append(f'成品水分低于标准下限 {lower_bound}（目标 {target}±{tolerance}）')
            elif finished > upper_bound:
                score += 40
                reasons.append(f'成品水分高于标准上限 {upper_bound}（目标 {target}±{tolerance}）')

            if finished_mean is not None and finished_std and abs(finished - finished_mean) >= 2 * finished_std:
                score += 30
                reasons.append(f'成品水分偏离均值 {round(finished_mean, 2)} 超过 2σ')

        if drying is not None and mixed is not None:
            diff = round(drying - mixed, 2)
            if math.fabs(diff) > DEFAULT_DIFF_LIMIT:
                score += 20
                reasons.append(f'烘丝到混合丝差值异常 {diff}')

        if mixed is not None and cabinet is not None:
            diff = round(mixed - cabinet, 2)
            if math.fabs(diff) > DEFAULT_DIFF_LIMIT:
                score += 20
                reasons.append(f'混合丝到出柜差值异常 {diff}')

        if drying is not None and finished is not None:
            diff = round(drying - finished, 2)
            if math.fabs(diff) > DEFAULT_DIFF_LIMIT:
                score += 15
                reasons.append(f'烘丝到成品差值偏大 {diff}')

        if cabinet is None:
            score += 10
            reasons.append('出柜水分缺失')
        if powder_rate is None:
            score += 5
            reasons.append('含末率缺失')

        if reasons:
            records.append(
                {
                    'id': row['id'],
                    'brand_id': row['brand_id'],
                    'brand_name': row['brand__name'],
                    'sampling_date': row['sampling_date'],
                    'sample_number': row['sample_number'],
                    'machine_number': row['machine_number'],
                    'machine_stage': row['machine_stage'],
                    'shift': row['shift'],
                    'addition_method': row['addition_method'],
                    'batch_number': row['batch_number'],
                    'finished_moisture': finished,
                    'drying_moisture': drying,
                    'mixed_moisture': mixed,
                    'cabinet_moisture': cabinet,
                    'rolling_moisture': _to_float(row['rolling_moisture']),
                    'powder_rate': powder_rate,
                    'risk_score': score,
                    'risk_level': 'high' if score >= 60 else 'medium' if score >= 30 else 'low',
                    'reasons': reasons,
                }
            )

    records.sort(key=lambda item: (-item['risk_score'], -item['id']))
    return {
        'summary': {
            'brand_id': brand_id,
            'total_records': len(rows),
            'anomaly_count': len(records),
            'high_risk_count': sum(1 for item in records if item['risk_level'] == 'high'),
            'medium_risk_count': sum(1 for item in records if item['risk_level'] == 'medium'),
            'low_risk_count': sum(1 for item in records if item['risk_level'] == 'low'),
            'finished_mean': round(finished_mean, 3) if finished_mean is not None else None,
            'finished_std': round(finished_std, 3) if finished_values else None,
            'target_range': {
                'min': round(DEFAULT_TARGET_MOISTURE - DEFAULT_TOLERANCE, 2),
                'max': round(DEFAULT_TARGET_MOISTURE + DEFAULT_TOLERANCE, 2),
            },
        },
        'records': records[:limit],
    }
