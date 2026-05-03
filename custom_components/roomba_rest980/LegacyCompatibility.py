"""Bring back the sensor attributes from the YAML config."""

from homeassistant.util import dt as dt_util

from .const import (
    binMappings,
    cleanBaseMappings,
    cycleMappings,
    errorMappings,
    jobInitiatorMappings,
    mopRanks,
    notReadyMappings,
    padMappings,
    phaseMappings,
    yesNoMappings,
)


def createExtendedAttributes(self) -> dict[str, any]:
    """Return all the given attributes from rest980."""
    data = self.coordinator.data or {}
    status = data.get("cleanMissionStatus", {})
    # Mission State
    cycle = status.get("cycle")
    phase = status.get("phase")
    err = status.get("error")
    notReady = status.get("notReady")
    initiator = status.get("initiator")
    missionStartTime = status.get("mssnStrtTm")
    rechargeTime = status.get("rechrgTm")
    expireTime = status.get("expireTm")
    # Generic Data
    softwareVer = data.get("softwareVer")
    vacuumHigh = data.get("vacHigh")
    carpetBoost = data.get("carpetBoost")
    if vacuumHigh is not None:
        if not vacuumHigh and not carpetBoost:
            robotCarpetBoost = "Eco"
        elif vacuumHigh and not carpetBoost:
            robotCarpetBoost = "Performance"
        else:
            robotCarpetBoost = "Auto"
    else:
        robotCarpetBoost = "n-a"
    battery = data.get("batPct")
    if softwareVer and "+" in softwareVer:
        softwareVer = softwareVer.split("+")[1]
    if cycle == "none" and notReady == 39:
        extv = "Pending"
    elif notReady and notReady > 0:
        extv = f"Not Ready ({notReady})"
    else:
        extv = cycleMappings.get(cycle, cycle)
    if phase == "charge" and battery == 100:
        rPhase = "Idle"
    elif cycle == "none" and phase == "stop":
        rPhase = "Stopped"
    else:
        rPhase = phaseMappings.get(phase, phase)
    def _minutes_since(ts: int | None) -> int | None:
        """Return minutes between an epoch timestamp and now, or None."""
        if not ts:
            return None
        return round((dt_util.utcnow().timestamp() - ts) / 60)

    def _format_minutes(minutes: int | None, long_form: bool) -> str:
        """Format a minute count as either `Nm` or `Hh MMm`."""
        if minutes is None:
            return "n-a"
        if long_form:
            return f"{minutes // 60}h {minutes % 60:0>2d}m"
        return f"{minutes}m"

    elapsed = _minutes_since(missionStartTime)
    long_form = elapsed is not None and elapsed > 60
    jobTime = _format_minutes(elapsed, long_form)
    jobResumeTime = _format_minutes(_minutes_since(rechargeTime), long_form)
    jobExpireTime = _format_minutes(_minutes_since(expireTime), long_form)
    # Bin
    robotBin = data.get("bin", {"full": False, "present": False})
    binFull = robotBin.get("full")
    binPresent = robotBin.get("present")
    # Dock
    dock = data.get("dock") or {}
    dockState = dock.get("state")
    # Pose
    ## NOTE: My roomba's firmware does not support this anymore, so I'm blindly guessing based on the previous YAML integration details.
    pose = data.get("pose") or {}
    theta = pose.get("theta")
    point = pose.get("point") or {}
    pointX = point.get("x")
    pointY = point.get("y")
    if theta is not None:
        location = f"{pointX}, {pointY}, {theta}"
    else:
        location = "n-a"
    # Networking
    signal = data.get("signal") or {}
    rssi = signal.get("rssi")
    # Runtime Statistics
    runtimeStats = data.get("runtimeStats")
    sqft = runtimeStats.get("sqft") if runtimeStats is not None else None
    hr = runtimeStats.get("hr") if runtimeStats is not None else None
    timeMin = runtimeStats.get("min") if runtimeStats is not None else None
    # Mission totals
    bbmssn = data.get("bbmssn") or {}
    numMissions = bbmssn.get("nMssn")
    # Run totals
    bbrun = data.get("bbrun") or {}
    numDirt = bbrun.get("nScrubs")
    numEvacs = bbrun.get("nEvacs")
    # numEvacs only for I7+/S9+ Models (Clean Base)
    pmaps = data.get("pmaps", [])
    pmap0id = next(iter(pmaps[0]), None) if pmaps and pmaps[0] else None
    noAutoPasses = data.get("noAutoPasses")
    twoPass = data.get("twoPass")
    if noAutoPasses is not None and twoPass is not None:
        if noAutoPasses is True and twoPass is False:
            robotCleanMode = "One"
        elif noAutoPasses is True and twoPass is True:
            robotCleanMode = "Two"
        else:
            robotCleanMode = "Auto"
    else:
        robotCleanMode = "n-a"

    if isinstance(sqft, (int, float)):
        total_area = f"{round(sqft / 10.764 * 100)}m²"
    else:
        total_area = None

    if hr is not None and timeMin is not None:
        total_time = f"{hr}h {timeMin}m"
    else:
        total_time = "n-a"

    robotObject = {
        "extendedStatus": extv,
        "notready_msg": notReadyMappings.get(notReady, notReady),
        "error_msg": errorMappings.get(err, err),
        "battery": f"{battery}%",
        "software_ver": softwareVer,
        "phase": rPhase,
        "bin": binMappings.get(binFull, binFull),
        "bin_present": yesNoMappings.get(binPresent, binPresent),
        "clean_base": cleanBaseMappings.get(dockState, dockState),
        "location": location,
        "rssi": rssi,
        "total_area": total_area,
        "total_time": total_time,
        "total_jobs": numMissions,
        "dirt_events": numDirt,
        "evac_events": numEvacs,
        "job_initiator": jobInitiatorMappings.get(initiator, initiator),
        "job_time": jobTime,
        "job_recharge": jobResumeTime,
        "job_expire": jobExpireTime,
        "clean_mode": robotCleanMode,
        "carpet_boost": robotCarpetBoost,
        "clean_edges": "true" if not data.get("openOnly", False) else "false",
        "maint_due": False,
        "pmap0_id": pmap0id,
    }

    if data.get("padWetness"):
        # It's a mop
        # TODO: Make sure this works! I don't own a mop, so I'm just re-using what jeremywillans has written.
        pad = data.get("padWetness", {})
        if isinstance(pad, dict):
            # priority: disposable > reusable
            if "disposable" in pad:
                robotCleanMode = pad["disposable"]
            elif "reusable" in pad:
                robotCleanMode = pad["reusable"]
            else:
                robotCleanMode = 0
        else:
            robotCleanMode = pad
        mopRankOverlap = data.get("rankOverlap")
        if not mopRankOverlap:
            robotObject["mop_behavior"] = "n-a"
        else:
            robotObject["mop_behavior"] = mopRanks.get(mopRankOverlap, mopRankOverlap)
        detectedPad = data.get("detectedPad")
        tankPresent = data.get("tankPresent")
        lidOpen = data.get("lidOpen")
        if detectedPad:
            robotObject["pad"] = padMappings.get(detectedPad)
        if tankPresent:
            if notReady == 31:  # Fill Tank
                robotObject["tank"] = "Fill Tank"
            elif not lidOpen:
                robotObject["tank"] = "Ready"
            elif lidOpen:
                robotObject["tank"] = "Lid Open"
        else:
            robotObject["tank"] = "Tank Missing"

    return robotObject
