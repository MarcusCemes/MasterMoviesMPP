<?php 

require('private/authenticate.php');

function binToUUID($binary) {
    $uuid = unpack("H*", $binary)['1'];
    $uuid_array = preg_replace("/([0-9a-f]{8})([0-9a-f]{4})([0-9a-f]{4})([0-9a-f]{4})([0-9a-f]{12})/", "$1-$2-$3-$4-$5", $uuid);
    return $uuid_array;
}

if ($_SESSION['AUTHENTICATED'] == true) {
    
    $result = $mysqli->query("SELECT jobID, jobUUID, sourceName, dateAdded, dateCompleted, status, BIN(completed) as completed, BIN(failed) as failed FROM job ORDER BY jobID DESC");
    echo $mysqli->error;
    $jobs = array();
    while ($row = $result->fetch_assoc()) {
        $row['jobUUID'] = binToUUID($row['jobUUID']);
        array_push($jobs, $row);
    }
    $result->close();
    
    $result = $mysqli->query("SELECT ingestJobID, status, failures, fk_jobUUID, fk_nodeUUID FROM ingestJob ORDER BY ingestJobID DESC");
    while ($row = $result->fetch_assoc()) {
        $row['fk_jobUUID'] = binToUUID($row['fk_jobUUID']);
        if (isset($row['fk_nodeUUID'])) $row['fk_nodeUUID'] = binToUUID($row['fk_nodeUUID']);
        foreach($jobs as $key => $item){
            if ($item['jobUUID'] == $row['fk_jobUUID']) {
                $jobs[$key]['ingestJob'] = $row;
                break;
            }
        }
    }
    $result->close();
    
    $result = $mysqli->query("SELECT transcodeJobID, status, failures, fk_jobUUID, fk_nodeUUID FROM transcodeJob ORDER BY transcodeJobID DESC");
    while ($row = $result->fetch_assoc()) {
        $row['fk_jobUUID'] = binToUUID($row['fk_jobUUID']);
        if (isset($row['fk_nodeUUID'])) $row['fk_nodeUUID'] = binToUUID($row['fk_nodeUUID']);
        foreach($jobs as $key => $item){
            if ($item['jobUUID'] == $row['fk_jobUUID']) {
                if (!isset($jobs[$key]['transcodeJob'])) $jobs[$key]['transcodeJob'] = array();
                array_push($jobs[$key]['transcodeJob'], $row);
                break;
            }
        }
    }
    $result->close();
    
    $result = $mysqli->query("SELECT exportJobID, status, failures, fk_jobUUID, fk_nodeUUID FROM exportJob ORDER BY exportJobID DESC");
    while ($row = $result->fetch_assoc()) {
        $row['fk_jobUUID'] = binToUUID($row['fk_jobUUID']);
        if (isset($row['fk_nodeUUID'])) $row['fk_nodeUUID'] = binToUUID($row['fk_nodeUUID']);
        foreach($jobs as $key => $item){
            if ($item['jobUUID'] == $row['fk_jobUUID']) {
                $jobs[$key]['exportJob'] = $row;
                break;
            }
        }
    }
    $result->close();
    
    
    $nodes = array();
    $result = $mysqli->query("SELECT nodeID, nodeUUID, lastAccess, type, BIN(isActive) AS isActive, BIN(terminate) AS terminate, BIN(authorise) AS authorise FROM node ORDER BY nodeID DESC");
    while ($row = $result->fetch_assoc()) {
        $row['nodeUUID'] = binToUUID($row['nodeUUID']);
        if (isset($row['fk_jobUUID'])) $row['fk_jobUUID'] = binToUUID($row['fk_jobUUID']);
        array_push($nodes, $row);
    }
    $result->close();
    
    
    $policies = array();
    $result = $mysqli->query("SELECT policyID, policy, value, value_type FROM policy ORDER BY policyID ASC");
    while ($row = $result->fetch_assoc()) {
        array_push($policies, $row);
    }
    $result->close();
    
    echo json_encode( array( 'jobs'=>$jobs, 'nodes'=>$nodes, 'policies'=>$policies ) );
    
} else {
    die(json_encode(array(
        'authenticated'=>0,
        'error'=> 'Not logged-in'
    )));
}


$mysqli->close();
?>