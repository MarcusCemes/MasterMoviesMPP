<?php

require('private/authenticate.php');

$response = array();

if ($_SESSION['AUTHENTICATED'] != true) {
    $response['authenticated'] = 0;
    $response['success'] = 0;
    $response['error'] = 'Not logged in';
} else {
    
    $response['authenticated'] = 1;
    
    if (!isset($_REQUEST['CMD'])) {
        $response['success'] = 0;
        $response['error'] = 'Missing command';
    } else {
        
        require_once('private/database_connection.php');
        $cmd = $_REQUEST['CMD'];
        $response['cmd'] = $cmd;
        
        if (strcasecmp($cmd, 'new_job') == 0) {
            
            if (empty($_REQUEST['source_name'])) {
            } else {
                $name = $_REQUEST['source_name'];
                $statement = $mysqli->prepare('INSERT INTO job (sourceName, dateAdded) VALUES (?, CURRENT_TIMESTAMP);');
                $statement->bind_param("s", $name);
                $success = $statement->execute();
                
                if ($success == true) {
                    $response['success'] = 1;
                } else {
                    $response['success'] = 0;
                    $response['error'] = 'SQL server failed to create the job';
                }
                
            }
            
            
        } else if (strcasecmp($cmd, 'delete_job') == 0) {
            
            if (empty($_REQUEST['ids'])) {
                $response['success'] = 0;
                $response['error'] = 'No videos given to delete';
            } else {
                
                $ids = json_decode($_REQUEST['ids']);
                
                if (gettype($ids) !== 'array') {
                    $response['success'] = 0;
                    $response['error'] = 'Bad list';
                } else {
                    $total_success = true;
                    for ($i = 0;$i<count($ids);$i++) {
                        $statement = $mysqli->prepare('DELETE FROM job WHERE jobID = ?');
                        $statement->bind_param("i", $ids[$i]);
                        $success = $statement->execute();
                        if ($success == false) {
                            $total_success = false;
                        }
                        $statement->close();
                    }
                    
                    if ($total_success == true) {
                        $response['success'] = 1;
                    } else {
                        $response['success'] = 2;
                        $response['error'] = 'Partial completion';
                    }
                
                }
            }
            
            
        } else if (strcasecmp($cmd, 'authorise_node') == 0) {
            if (empty($_REQUEST['ids'])) {
                $response['success'] = 0;
                $response['error'] = 'No nodes given to enable';
            } else {
                $ids = json_decode($_REQUEST['ids']);
                $total_success = true;
                    for ($i = 0;$i<count($ids);$i++) {
                        $statement = $mysqli->prepare('UPDATE node SET authorise = 1 WHERE nodeID = ?');
                        $statement->bind_param("i", $ids[$i]);
                        $success = $statement->execute();
                        if ($success == false) {
                            $total_success = false;
                        }
                        $statement->close();
                    }
                    
                    if ($total_success == true) {
                        $response['success'] = 1;
                    } else {
                        $response['success'] = 2;
                        $response['error'] = 'Partial completion';
                    }
            }
            
        } else if (strcasecmp($cmd, 'deauthorise_node') == 0) {
            if (empty($_REQUEST['ids'])) {
                $response['success'] = 0;
                $response['error'] = 'No nodes given to disable';
            } else {
                $ids = json_decode($_REQUEST['ids']);
                $total_success = true;
                    for ($i = 0;$i<count($ids);$i++) {
                        $statement = $mysqli->prepare('UPDATE node SET authorise = 0 WHERE nodeID = ?');
                        $statement->bind_param("i", $ids[$i]);
                        $success = $statement->execute();
                        if ($success == false) {
                            $total_success = false;
                        }
                        $statement->close();
                    }
                    
                    if ($total_success == true) {
                        $response['success'] = 1;
                    } else {
                        $response['success'] = 2;
                        $response['error'] = 'Partial completion';
                    }
            }
        } else if (strcasecmp($cmd, 'terminate_node') == 0) {
            if (empty($_REQUEST['ids'])) {
                $response['success'] = 0;
                $response['error'] = 'No nodes given to terminate';
            } else {
                $ids = json_decode($_REQUEST['ids']);
                $total_success = true;
                    for ($i = 0;$i<count($ids);$i++) {
                        $statement = $mysqli->prepare('UPDATE node SET terminate = 1 WHERE nodeID = ?');
                        $statement->bind_param("i", $ids[$i]);
                        $success = $statement->execute();
                        if ($success == false) {
                            $total_success = false;
                        }
                        $statement->close();
                    }
                    
                    if ($total_success == true) {
                        $response['success'] = 1;
                    } else {
                        $response['success'] = 2;
                        $response['error'] = 'Partial completion';
                    }
            }
        } else if (strcasecmp($cmd, 'update_policy') == 0) {
            if (empty($_REQUEST['policies'])) {
                $response['success'] = 0;
                $response['error'] = 'No policies given to update';
            } else {
                $policies = json_decode($_REQUEST['policies'], true);
                $total_success = true;
                foreach ($policies as $key => $value) {
                    $statement = $mysqli->prepare('UPDATE policy SET value = ? WHERE policy = ?');
                    $statement->bind_param("ss", $value, $key);
                    $success = $statement->execute();
                    $response['sqlerror'] = $mysqli->error;
                    if ($success == false) {
                        $total_success = false;
                    }
                    $statement->close();
                }

                if ($total_success == true) {
                    $response['success'] = 1;
                } else {
                    $response['success'] = 2;
                    $response['error'] = 'Partial completion';
                }
                
            }
        } else {
            
            $response['success'] = 0;
            $response['error'] = 'Unknown command';
        }
    }
}

echo json_encode($response);


?>
